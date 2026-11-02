"""Meep 冒煙測試：2D 直波導（n=3.48，寬 0.5 µm）CW 光源，跑到 t=50，量穿透通量。只確認能計算，不是設計數據。"""
import meep as mp

cell = mp.Vector3(8, 4)
geom = [mp.Block(mp.Vector3(mp.inf, 0.5), material=mp.Medium(index=3.48))]
src = [mp.Source(mp.ContinuousSource(frequency=1 / 1.55), component=mp.Ez, center=mp.Vector3(-3, 0),
                 size=mp.Vector3(0, 1))]
sim = mp.Simulation(cell_size=cell, geometry=geom, sources=src, boundary_layers=[mp.PML(1.0)], resolution=20)
flux = sim.add_flux(1 / 1.55, 0, 1, mp.FluxRegion(center=mp.Vector3(3, 0), size=mp.Vector3(0, 2)))
sim.run(until=50)
print("MEEP_SMOKE_OK", mp.__version__, "flux", round(mp.get_fluxes(flux)[0], 4))
