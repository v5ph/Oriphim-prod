/*
  ORIPHIM RENDERER 1.0.0
  ======================
  A fixed, versioned renderer. It is audited once; it does not change per run.
  Everything variable lives in two JSON documents it consumes:

    SCENE  — what to draw and how (written by the model, small, declarative)
    DATA   — solver output frames (written by the pipeline, never by the model)

  The renderer invents no motion. Every position it draws came from DATA.
  Attach them as <script type="application/json" id="oriphim-scene"> and
  id="oriphim-data">, or set window.ORIPHIM_SCENE / window.ORIPHIM_DATA before
  this script runs. With neither present it falls back to clearly-labelled
  synthetic demo data so the file is viewable standalone.

  Provenance: Oriphim.stamp() returns the renderer version, a hash of the scene,
  a hash of the data, and the resolved world scale. Put that in the report.

  Deliberate constraints, because this is a verification product:
    - No auto-normalisation per frame. Scalar ranges are explicit, or computed
      once over the whole run and recorded in the stamp.
    - No frame interpolation unless the scene asks for it. The default shows
      solver frames as they are.
    - No procedural motion, ever. Aesthetic choices affect shading only.

  This file is vendored verbatim from the audited reference. Do not edit it to
  fit a run; bump the version and re-audit instead.
*/

(() => {
"use strict";

const RENDERER_VERSION = "1.0.0";

// ---- small helpers -------------------------------------------------------
function fnv1a(str){
  let h = 0x811c9dc5;
  for(let i=0;i<str.length;i++){ h ^= str.charCodeAt(i); h = Math.imul(h, 0x01000193); }
  return ("00000000"+(h>>>0).toString(16)).slice(-8);
}
function h3(i,j,k){
  let n = Math.imul(i|0,374761393) ^ Math.imul(j|0,668265263) ^ Math.imul(k|0,1442695041);
  n = Math.imul(n ^ (n>>>13), 1274126177);
  return ((n ^ (n>>>16))>>>0) * 2.3283064365386963e-10;
}
function fib(n){                                  // fibonacci sphere directions
  const P=new Float32Array(n*3), ga=Math.PI*(3-Math.sqrt(5));
  for(let i=0;i<n;i++){
    const y=1-2*(i+0.5)/n, r=Math.sqrt(Math.max(0,1-y*y)), th=i*ga;
    P[i*3]=Math.cos(th)*r; P[i*3+1]=y; P[i*3+2]=Math.sin(th)*r;
  }
  return P;
}
function shuffled(n, seed0){
  const o=new Uint32Array(n);
  for(let i=0;i<n;i++) o[i]=i;
  let s=seed0|0 || 0x9e3779b9;
  const rnd=()=>{ s=Math.imul(s^(s>>>15),0x2545f491); return ((s>>>0)%1000000)/1000000; };
  for(let i=n-1;i>0;i--){ const j=(rnd()*(i+1))|0; const t=o[i]; o[i]=o[j]; o[j]=t; }
  return o;
}
const BAYER = (()=>{
  const m=[0,32,8,40,2,34,10,42,48,16,56,24,50,18,58,26,12,44,4,36,14,46,6,38,
           60,28,52,20,62,30,54,22,3,35,11,43,1,33,9,41,51,19,59,27,49,17,57,25,
           15,47,7,39,13,45,5,37,63,31,55,23,61,29,53,21];
  const b=new Float32Array(64);
  for(let i=0;i<64;i++) b[i]=(m[i]+0.5)/64;
  return b;
})();

// ---- defaults ------------------------------------------------------------
const DEFAULTS = {
  style:  {cell:2, voxpx:1.8, chroma:1.0, gamma:0.88, light:[-0.44,0.55,0.71], depthFade:0.38},
  camera: {size:0.34, zoom:1, tilt:-0.30, yaw:0, spin:0.45, interactive:true,
           zoomMin:0.2, zoomMax:8, grabFraction:0.86},
  playback:{fps:30, speed:1, loop:true, interpolate:false},
  world:  {scale:1, center:[0,0,0], fit:"none"}    // "none" | "once"
};
const merge = (d,o)=>Object.assign({}, d, o||{});

// ==========================================================================
//  RENDERER
// ==========================================================================
function mount(host, scene, data){
  scene = scene || {};
  data  = data  || {frames:1, tracks:{}};

  const style    = merge(DEFAULTS.style,    scene.style);
  const camera   = merge(DEFAULTS.camera,   scene.camera);
  const playback = merge(DEFAULTS.playback, scene.playback);
  const world    = merge(DEFAULTS.world,    scene.world);
  const objects  = scene.objects || [];

  // ---- world fit: resolved ONCE, never per frame -------------------------
  let worldScale = world.scale, worldCenter = world.center.slice();
  if(world.fit === "once"){
    let mx=0;
    for(const key in data.tracks){
      const t=data.tracks[key];
      for(let f=0; f<t.positions.length; f++){
        const P=t.positions[f];
        for(let i=0;i<P.length;i+=3){
          const dx=P[i]-worldCenter[0], dy=P[i+1]-worldCenter[1], dz=P[i+2]-worldCenter[2];
          const d=Math.sqrt(dx*dx+dy*dy+dz*dz);
          if(d>mx) mx=d;
        }
      }
    }
    if(mx>0) worldScale = 1.0/mx;
  }

  // ---- scalar ranges: explicit, or computed once and recorded -----------
  const scalarRange = {};
  for(const o of objects){
    if(!o.scalar) continue;
    const key = o.track+"::"+o.scalar;
    if(scalarRange[key]) continue;
    if(o.range){ scalarRange[key] = o.range.slice(); continue; }
    const t=data.tracks[o.track];
    let lo=Infinity, hi=-Infinity;
    if(t && t.scalars && t.scalars[o.scalar]){
      const S=t.scalars[o.scalar];
      for(let f=0;f<S.length;f++) for(let i=0;i<S[f].length;i++){
        const v=S[f][i]; if(v<lo)lo=v; if(v>hi)hi=v;
      }
    }
    scalarRange[key] = (lo<hi) ? [lo,hi] : [0,1];
  }

  // ---- per-object cached point tables ------------------------------------
  for(const o of objects){
    if(o.type==="shell"){
      const n = o.points || 9000;
      o._pts = fib(n);
      o._ord = shuffled(n, 0x9e3779b9 ^ fnv1a(o.id||o.track||"shell").charCodeAt(0));
    }
  }

  // ---- DOM ---------------------------------------------------------------
  const cv = document.createElement('canvas');
  cv.className = 'oriphim-canvas';
  host.appendChild(cv);
  const ctx = cv.getContext('2d');
  const off = document.createElement('canvas');
  const octx = off.getContext('2d');

  let grab = null;
  if(camera.interactive){
    grab = document.createElement('div');
    grab.className = 'oriphim-grab';
    host.appendChild(grab);
  }

  let gw=0, gh=0, img=null, buf32=null, buf8=null;
  let depth=null, val=null, chb=null;
  let R=0, cxg=0, cyg=0, G=70, sSize=2;
  let zoom = camera.zoom, voxpx = style.voxpx;
  const LX=style.light[0], LY=style.light[1], LZ=style.light[2];

  function resize(){
    const dpr = Math.min(devicePixelRatio||1, 2);
    const W = host.clientWidth || innerWidth, H = host.clientHeight || innerHeight;
    cv.width = Math.round(W*dpr); cv.height = Math.round(H*dpr);
    gw = Math.max(8, Math.ceil(W/style.cell));
    gh = Math.max(8, Math.ceil(H/style.cell));
    off.width=gw; off.height=gh;
    img = octx.createImageData(gw,gh);
    const ab = new ArrayBuffer(gw*gh*4);
    buf32=new Uint32Array(ab); buf8=new Uint8ClampedArray(ab);
    depth=new Float32Array(gw*gh); val=new Float32Array(gw*gh); chb=new Float32Array(gw*gh);
    ctx.imageSmoothingEnabled=false;
    if(grab){
      const dia=Math.min(W,H)*camera.grabFraction;
      grab.style.width=grab.style.height=dia+'px';
      grab.style.left=(W*0.5-dia*0.5)+'px';
      grab.style.top =(H*0.5-dia*0.5)+'px';
    }
  }
  addEventListener('resize', resize);
  if(window.ResizeObserver) new ResizeObserver(resize).observe(host);

  // ---- orientation -------------------------------------------------------
  const M=new Float32Array([1,0,0, 0,1,0, 0,0,1]);
  function rotX(a){
    const c=Math.cos(a), s=Math.sin(a);
    const a3=M[3],a4=M[4],a5=M[5], a6=M[6],a7=M[7],a8=M[8];
    M[3]=c*a3-s*a6; M[4]=c*a4-s*a7; M[5]=c*a5-s*a8;
    M[6]=s*a3+c*a6; M[7]=s*a4+c*a7; M[8]=s*a5+c*a8;
  }
  function rotY(a){
    const c=Math.cos(a), s=Math.sin(a);
    const a0=M[0],a1=M[1],a2=M[2], a6=M[6],a7=M[7],a8=M[8];
    M[0]=c*a0+s*a6; M[1]=c*a1+s*a7; M[2]=c*a2+s*a8;
    M[6]=-s*a0+c*a6; M[7]=-s*a1+c*a7; M[8]=-s*a2+c*a8;
  }
  rotX(camera.tilt); if(camera.yaw) rotY(camera.yaw);

  let dragging=false, lx=0, ly=0, vxD=0, vyD=0, ldt=1, idle=1;
  if(grab){
    const K=0.007, pts=new Map();
    let pinchD=0, pinchZ=1;
    const clampZ=z=>Math.max(camera.zoomMin, Math.min(camera.zoomMax, z));
    grab.addEventListener('pointerdown', e=>{
      pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
      grab.setPointerCapture(e.pointerId);
      if(pts.size===2){
        dragging=false; vxD=0; vyD=0;
        const [a,b]=[...pts.values()];
        pinchD=Math.hypot(a.x-b.x,a.y-b.y)||1; pinchZ=zoom;
      } else { dragging=true; lx=e.clientX; ly=e.clientY; vxD=0; vyD=0; idle=0; }
      e.preventDefault();
    });
    const drop=e=>{
      pts.delete(e.pointerId);
      if(pts.size<2) pinchD=0;
      if(pts.size===0) dragging=false;
      else if(pts.size===1){ const p=[...pts.values()][0]; lx=p.x; ly=p.y; dragging=true; idle=0; }
    };
    grab.addEventListener('pointerup', drop);
    grab.addEventListener('pointercancel', drop);
    grab.addEventListener('pointerleave', drop);
    grab.addEventListener('pointermove', e=>{
      if(pts.has(e.pointerId)) pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
      if(pts.size===2 && pinchD){
        const [a,b]=[...pts.values()];
        zoom=clampZ(pinchZ*((Math.hypot(a.x-b.x,a.y-b.y)||1)/pinchD));
        e.preventDefault(); return;
      }
      if(!dragging) return;
      const dx=e.clientX-lx, dy=e.clientY-ly;
      rotY(dx*K); rotX(dy*K);
      const inv=1/Math.max(ldt,0.008);
      vxD=Math.max(-8,Math.min(8,dx*K*inv));
      vyD=Math.max(-8,Math.min(8,dy*K*inv));
      lx=e.clientX; ly=e.clientY; e.preventDefault();
    });
    grab.addEventListener('wheel', e=>{
      e.preventDefault();
      const f=Math.exp(-e.deltaY*0.0016);
      if(e.shiftKey) voxpx=Math.max(1, Math.min(9, voxpx*f));
      else           zoom=clampZ(zoom*f);
    }, {passive:false});
  }

  // ---- raster primitives -------------------------------------------------
  function splat(wx,wy,wz,v,cm,s){
    const X=Math.round(wx*G)/G, Y=Math.round(wy*G)/G, Z=Math.round(wz*G)/G;
    const half=s*0.5;
    const x0=(cxg+X*R-half)|0, y0=(cyg-Y*R-half)|0;
    for(let yy=y0; yy<y0+s; yy++){
      if(yy<0||yy>=gh) continue;
      const ro=yy*gw;
      for(let xx=x0; xx<x0+s; xx++){
        if(xx<0||xx>=gw) continue;
        const idx=ro+xx;
        if(Z>depth[idx]){ depth[idx]=Z; val[idx]=v; chb[idx]=cm; }
      }
    }
  }
  function ball(wx,wy,wz,nv,v,cm){
    const n=Math.ceil(nv), n2=nv*nv;
    const inr=Math.max(0,nv-1.25), in2=inr*inr, st=1/G;
    for(let oz=-n;oz<=n;oz++) for(let oy=-n;oy<=n;oy++) for(let ox=-n;ox<=n;ox++){
      const d2=ox*ox+oy*oy+oz*oz;
      if(d2>n2||d2<in2) continue;
      const inv=1/Math.sqrt(d2||1), nzs=oz*inv;
      if(nzs<-0.30) continue;
      const lam=Math.max(0, ox*inv*LX + oy*inv*LY + nzs*LZ);
      const az=nzs<0?-nzs:nzs;
      splat(wx+ox*st, wy+oy*st, wz+oz*st,
            v*(0.26+0.90*lam)+v*0.45*Math.pow(1-az,5), cm, sSize);
    }
  }

  // ---- frame selection ---------------------------------------------------
  const nFrames = Math.max(1, data.frames|0);
  let clock = 0;
  function frameCursor(){
    const f = clock*playback.fps*playback.speed;
    if(!playback.loop && f >= nFrames-1) return {i:nFrames-1, j:nFrames-1, t:0};
    const w = f % nFrames;
    const i = Math.floor(w) % nFrames;
    const j = (i+1) % nFrames;
    return {i, j, t: playback.interpolate ? (w-Math.floor(w)) : 0};
  }
  function posAt(track, cur){
    const t = data.tracks[track];
    if(!t) return null;
    const A = t.positions[Math.min(cur.i, t.positions.length-1)];
    if(!cur.t) return A;
    const B = t.positions[Math.min(cur.j, t.positions.length-1)];
    if(!B || B.length!==A.length) return A;
    const out=new Float32Array(A.length);
    for(let i=0;i<A.length;i++) out[i]=A[i]+(B[i]-A[i])*cur.t;
    return out;
  }
  function scalarAt(track, name, cur){
    const t=data.tracks[track];
    if(!t || !t.scalars || !t.scalars[name]) return null;
    return t.scalars[name][Math.min(cur.i, t.scalars[name].length-1)];
  }

  const wx_ = (x)=> (x-worldCenter[0])*worldScale;
  const wy_ = (y)=> (y-worldCenter[1])*worldScale;
  const wz_ = (z)=> (z-worldCenter[2])*worldScale;

  // ---- draw --------------------------------------------------------------
  function draw(){
    cxg=gw*0.5; cyg=gh*0.5;
    R=Math.min(gw,gh)*camera.size*zoom;
    G=Math.max(6, R/voxpx);
    sSize=Math.max(1, Math.round(voxpx));
    const m0=M[0],m1=M[1],m2=M[2],m3=M[3],m4=M[4],m5=M[5],m6=M[6],m7=M[7],m8=M[8];
    const DF=style.depthFade;
    const cur=frameCursor();

    depth.fill(-1e9);

    for(const o of objects){
      const P = posAt(o.track, cur);
      if(!P) continue;
      const base = (o.brightness!=null) ? o.brightness : 1.0;

      // -------- shell: a body with a radius, drawn as a lit point shell ----
      if(o.type==="shell"){
        const cx=wx_(P[0]), cy=wy_(P[1]), cz=wz_(P[2]);
        const rad=(o.radius||0.1)*worldScale;
        const pts=o._pts, ord=o._ord, n=pts.length/3;
        const dark = !!o.dark;                       // e.g. an event horizon
        for(let k=0;k<n;k++){
          const i=ord[k]*3;
          const dx=pts[i], dy=pts[i+1], dz=pts[i+2];
          const nx=m0*dx+m1*dy+m2*dz, ny=m3*dx+m4*dy+m5*dz, nz=m6*dx+m7*dy+m8*dz;
          if(nz < -0.28) continue;
          const ax=nx<0?-nx:nx, ay=ny<0?-ny:ny, az=nz<0?-nz:nz;
          let face;
          if(az>=ax&&az>=ay) face=1.00;
          else if(ay>=ax)    face=ny>0?0.86:0.30;
          else               face=nx>0?0.60:0.46;
          const lam=Math.max(0, nx*LX+ny*LY+nz*LZ);
          const rim=Math.pow(1-az,5)*0.85;
          const X=cx+nx*rad, Y=cy+ny*rad, Z=cz+nz*rad;
          let v = dark ? (0.02 + 1.30*Math.pow(1-az,9))
                       : base*(face*(0.18+0.95*lam)+rim);
          v *= (1-DF) + DF*(Z+1.4)/2.8;
          splat(X,Y,Z, v, (lam-0.5)*0.6, sSize);
        }
      }

      // -------- curve: polyline, optionally widened into a ribbon ---------
      else if(o.type==="curve"){
        const K=P.length/3;
        const hw=(o.width||0)*worldScale*0.5;
        const wid=hw>0 ? (o.across||7) : 1;
        const twist=o.twist||0;
        let ux=0, uy=1, uz=0;                        // carried reference frame
        for(let k=0;k<K;k++){
          const i=k*3;
          const px=wx_(P[i]), py=wy_(P[i+1]), pz=wz_(P[i+2]);
          const i2=((k+1<K)?k+1:k-1)*3;
          let tx=wx_(P[i2])-px, ty=wy_(P[i2+1])-py, tz=wz_(P[i2+2])-pz;
          if(k+1>=K){ tx=-tx; ty=-ty; tz=-tz; }
          const tl=Math.hypot(tx,ty,tz)||1; tx/=tl; ty/=tl; tz/=tl;
          // parallel transport: remove the tangent component from the frame
          const d=ux*tx+uy*ty+uz*tz;
          ux-=tx*d; uy-=ty*d; uz-=tz*d;
          let ul=Math.hypot(ux,uy,uz);
          if(ul<1e-4){ ux=(Math.abs(tx)<0.9)?1:0; uy=(Math.abs(tx)<0.9)?0:1; uz=0;
                       const d2=ux*tx+uy*ty+uz*tz; ux-=tx*d2; uy-=ty*d2; uz-=tz*d2;
                       ul=Math.hypot(ux,uy,uz)||1; }
          ux/=ul; uy/=ul; uz/=ul;
          const vx2=ty*uz-tz*uy, vy2=tz*ux-tx*uz, vz2=tx*uy-ty*ux;
          const ang=twist*(k/K)*Math.PI*2;
          const ca=Math.cos(ang), sa=Math.sin(ang);
          const ax2=ux*ca+vx2*sa, ay2=uy*ca+vy2*sa, az2=uz*ca+vz2*sa;
          // surface normal of the strap
          let nx=ty*az2-tz*ay2, ny=tz*ax2-tx*az2, nz=tx*ay2-ty*ax2;
          const nl=Math.hypot(nx,ny,nz)||1; nx/=nl; ny/=nl; nz/=nl;
          const NX=m0*nx+m1*ny+m2*nz, NY=m3*nx+m4*ny+m5*nz, NZ=m6*nx+m7*ny+m8*nz;
          const lam=Math.abs(NX*LX+NY*LY+NZ*LZ);
          const azn=NZ<0?-NZ:NZ;
          for(let w=0;w<wid;w++){
            const s=(wid===1)?0:((w/(wid-1))*2-1);
            const qx=px+ax2*hw*s, qy=py+ay2*hw*s, qz=pz+az2*hw*s;
            const X=m0*qx+m1*qy+m2*qz, Y=m3*qx+m4*qy+m5*qz, Z=m6*qx+m7*qy+m8*qz;
            let v = base*(0.18+0.95*lam)*(0.74+0.32*Math.cos(s*1.35));
            v += Math.pow(1-azn,6)*0.50;
            v *= (1-DF)+DF*(Z+1.4)/2.8;
            splat(X,Y,Z, v, (lam-0.5)*0.7, sSize);
          }
        }
      }

      // -------- particles: one point per element, optional scalar ---------
      else if(o.type==="particles"){
        const S = o.scalar ? scalarAt(o.track, o.scalar, cur) : null;
        const rng = o.scalar ? scalarRange[o.track+"::"+o.scalar] : null;
        const lo = rng?rng[0]:0, span = rng?(rng[1]-rng[0])||1:1;
        const nv = Math.min(o.maxVoxels||4, (o.radius||0)*worldScale*G);
        const solid = nv>0.9;
        const margin = (solid?nv:1)*sSize+4;
        const n=P.length/3;
        for(let k=0;k<n;k++){
          const i=k*3;
          const px=wx_(P[i]), py=wy_(P[i+1]), pz=wz_(P[i+2]);
          const X=m0*px+m1*py+m2*pz, Y=m3*px+m4*py+m5*pz, Z=m6*px+m7*py+m8*pz;
          const sx=cxg+X*R, sy=cyg-Y*R;
          if(sx<-margin||sx>gw+margin||sy<-margin||sy>gh+margin) continue;
          let u = 0.5;
          if(S){ u=(S[k]-lo)/span; u=u<0?0:(u>1?1:u); }
          let v = base*((o.floor!=null?o.floor:0.26) + (o.gain!=null?o.gain:1.05)*u);
          v *= (1-DF)+DF*(Z+1.4)/2.8;
          const cm = u*1.3-0.35;
          if(solid) ball(X,Y,Z, nv, v, cm);
          else      splat(X,Y,Z, v, cm, sSize);
        }
      }
    }

    // ---- quantise: 8x8 Bayer, per-channel rotation for the chroma split --
    const CH=style.chroma, GA=style.gamma;
    for(let py=0,p=0; py<gh; py++){
      const brow=(py&7)<<3;
      for(let px=0; px<gw; px++, p++){
        if(depth[p] <= -1e8){ buf32[p]=0; continue; }
        let v=val[p];
        v=v<0?0:(v>1?1:v);
        v=Math.pow(v,GA);
        const bi=brow|(px&7);
        const tR=BAYER[bi];
        const tG=tR+(BAYER[(bi+21)&63]-tR)*CH;
        const tB=tR+(BAYER[(bi+42)&63]-tR)*CH;
        const o=chb[p]*CH*0.20;
        const r=(v+o>tR)?255:0, g=(v>tG)?255:0, b=(v-o>tB)?255:0;
        buf32[p]=0xff000000|(b<<16)|(g<<8)|r;
      }
    }
    img.data.set(buf8);
    octx.putImageData(img,0,0);
    ctx.clearRect(0,0,cv.width,cv.height);
    ctx.imageSmoothingEnabled=false;
    ctx.drawImage(off,0,0,cv.width,cv.height);
  }

  // ---- loop --------------------------------------------------------------
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let running = !reduce;
  let last=performance.now();
  function loop(now){
    const dt=Math.min(0.05,(now-last)/1000); last=now; ldt=dt;
    if(running) clock += dt;

    if(dragging){ idle=0; }
    else {
      if(vxD||vyD){
        rotY(vxD*dt); rotX(vyD*dt);
        const kk=Math.exp(-2.4*dt);
        vxD*=kk; vyD*=kk;
        if(Math.abs(vxD)<0.004) vxD=0;
        if(Math.abs(vyD)<0.004) vyD=0;
      }
      idle=Math.min(1, idle+dt*0.7);
      if(camera.spin) rotY(dt*0.10*camera.spin*idle);
    }
    draw();
    requestAnimationFrame(loop);
  }
  resize();
  requestAnimationFrame(loop);

  // ---- handle ------------------------------------------------------------
  return {
    version: RENDERER_VERSION,
    play(){ running=true; },
    pause(){ running=false; },
    seek(frame){ clock = frame/(playback.fps*playback.speed); draw(); },
    frameCount: nFrames,
    stamp(){
      return {
        renderer: RENDERER_VERSION,
        scene_hash: fnv1a(JSON.stringify(scene)),
        data_hash:  fnv1a(JSON.stringify(data.tracks||{})),
        run_id: (data.meta&&data.meta.run_id)||null,
        frames: nFrames,
        world_scale: worldScale,
        world_fit: world.fit,
        interpolated: !!playback.interpolate,
        scalar_ranges: scalarRange
      };
    },
    png(){ return cv.toDataURL('image/png'); }
  };
}

window.Oriphim = { version: RENDERER_VERSION, mount };

// ==========================================================================
//  BOOTSTRAP
// ==========================================================================
function readJSON(id){
  const el=document.getElementById(id);
  if(!el) return null;
  try { return JSON.parse(el.textContent); } catch(e){ console.error(id, e); return null; }
}

// ---- DEMO DATA — synthetic, NOT solver output. For viewing this file alone.
function demo(){
  const F=360, N=900;
  const hole=[], jet=[], line=[], temp=[];
  for(let f=0; f<F; f++){
    const t=f/F*Math.PI*2;
    hole.push([0,0,0]);
    const pj=new Float32Array(N*3), tj=new Float32Array(N);
    for(let i=0;i<N;i++){
      const r=0.35+0.65*h3(i,1,7);
      const a=h3(i,2,9)*Math.PI*2 + t*(1.8/Math.pow(r,1.5));
      const z=(h3(i,3,11)-0.5)*0.10*r;
      pj[i*3]=Math.cos(a)*r; pj[i*3+1]=z; pj[i*3+2]=Math.sin(a)*r;
      tj[i]=1/r;
    }
    jet.push(pj); temp.push(tj);
    const K=220, pl=new Float32Array(K*3);
    for(let k=0;k<K;k++){
      const u=k/(K-1)*Math.PI*2;
      pl[k*3]  =Math.cos(u)*1.15;
      pl[k*3+1]=Math.sin(u*2+t)*0.30;
      pl[k*3+2]=Math.sin(u)*1.15;
    }
    line.push(pl);
  }
  return {
    meta:{run_id:"DEMO-SYNTHETIC", solver:"none — illustrative only", units:"arbitrary"},
    frames:F,
    tracks:{
      core:{kind:"rigid",   positions:hole},
      disk:{kind:"points",  positions:jet, scalars:{temperature:temp}},
      loop:{kind:"polyline",positions:line}
    }
  };
}
const DEMO_SCENE = {
  version:"1.0.0",
  style:{cell:2, voxpx:1.8, chroma:1.0},
  camera:{size:0.34, zoom:1, tilt:-0.32, spin:0.45},
  playback:{fps:60, loop:true},
  world:{scale:1, center:[0,0,0], fit:"none"},
  objects:[
    {id:"core", type:"shell", track:"core", radius:0.20, points:9000, dark:true},
    {id:"disk", type:"particles", track:"disk", scalar:"temperature",
     radius:0.006, floor:0.30, gain:1.00},
    {id:"loop", type:"curve", track:"loop", width:0.07, across:8, twist:1}
  ],
  provenance:{note:"demo scene shipped with the renderer"}
};

const stage = document.getElementById('stage');
const scene = window.ORIPHIM_SCENE || readJSON('oriphim-scene') || DEMO_SCENE;
const data  = window.ORIPHIM_DATA  || readJSON('oriphim-data')  || demo();
window.oriphim = Oriphim.mount(stage, scene, data);
console.log("Oriphim renderer", RENDERER_VERSION, window.oriphim.stamp());
})();
