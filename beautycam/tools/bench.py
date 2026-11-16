import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np, cv2
from beautycam import imgops
from beautycam.selftest import synth_portrait

f = synth_portrait(1280, 720)
u8 = f
print("cv2 threads:", cv2.getNumThreads())

def t(name, fn, n=8):
    fn()
    t0=time.perf_counter()
    for _ in range(n): r=fn()
    dt=(time.perf_counter()-t0)/n*1000
    print(f"{name:28s} {dt:7.2f} ms")
    return r

fl = t("to float32", lambda: u8.astype(np.float32))
m  = t("skin_mask", lambda: imgops.skin_mask(u8))
sm = t("smooth(0.75)", lambda: imgops.smooth(fl, m, 0.75))
wh = t("whiten(0.45)", lambda: imgops.whiten(sm, m, 0.45))
ro = t("rosy(0.3)", lambda: imgops.rosy(wh, m, 0.3))
sh = t("sharpen(0.35)", lambda: imgops.sharpen(ro, m, 0.35))
mx,my = t("warp_maps", lambda: imgops.warp_maps(720,1280,0.35,0.0,0.5,0.46,0.22,0.30))
t("remap", lambda: cv2.remap(u8,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT101))
t("clip+cast", lambda: np.clip(sh,0,255).astype(np.uint8))
