"""Write real control GDS files with gdstk, not KLayout geometry export."""
from pathlib import Path
import gdstk,json,hashlib
def generate(source,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);cases=[]
    variants=[('Si_narrow',3,'width',.2,False),('Si_gap',3,'space',.15,False),('HT_narrow',39,'width',.4,False),('HT_gap',39,'space',5,False),('PAD_narrow',41,'width',1,False),('PAD_gap',41,'space',5,False),('Si_margin_equal',3,'width',.349,True),('Si_below_margin',3,'width',.348,False)]
    for name,layer,kind,size,passed in variants:
        lib=gdstk.read_gds(str(source));top=lib.top_level()[0]
        if kind=='width':top.add(gdstk.rectangle((3300,0),(3310,size),layer=layer))
        else:
            top.add(gdstk.rectangle((3300,0),(3320,20),layer=layer));top.add(gdstk.rectangle((3320+size,0),(3340+size,20),layer=layer))
        dest=folder/(name+'.gds');lib.write_gds(str(dest))
        cases.append(dict(id=name,layer=layer,kind=kind,inserted_dimension_um=size,expected_rule_passed=passed,gds=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
    return cases
