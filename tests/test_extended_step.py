import copy
import math
import pytest
from engineering_cad_converter import cad_pipeline as engine, step_model


def dimension(value):
    return {'value':value,'source_id':'S1','locator':'independent synthetic specification',
            'statement':f'Nominal value explicitly specified: {value}'}


def case(tmp_path, profile, points=None, features=None):
    source=tmp_path/'source.txt'
    source.write_text(f'Synthetic nominal definition: profile={profile}, vertices={points}, features={features}',encoding='utf-8')
    model={'units':'mm','fully_defined':True,'issues':[],'scope':'Explicit synthetic part',
        'datum':'XY extrusion +Z from z=0; or XZ section with radius from global Z axis',
        'physical_accuracy':'unknown','sources':[{'id':'S1','path':source.name,'sha256':engine.sha(source)}],
        'profile':profile,'dimensions':{'angle':dimension(360)} if profile=='revolution' else {'depth':dimension(5)},
        'expected':{'units':'mm','solids':1,'volume_mm3':1,'bbox_mm':[1,1,1],
            'tolerances':{'volume_mm3':1e-5,'bbox_mm':1e-5},'basis':'Independent formulas from synthetic source definition'}}
    if profile=='rectangle':model['dimensions'].update(width=dimension(20),height=dimension(10))
    if points:model['vertices']=[{'x':dimension(x),'y':dimension(y)} for x,y in points]
    if features:model['features']=features
    path=tmp_path/'model.json';engine.dump(path,model);return path,model


@pytest.mark.parametrize('profile,points,volume,bbox',[
    ('polygon',[(0,0),(10,0),(0,10)],250,[10,10,5]),
    ('revolution',[(3,0),(5,0),(5,10),(3,10)],160*math.pi,[10,10,10]),
])
def test_polygon_and_revolution_roundtrip(tmp_path,profile,points,volume,bbox):
    pytest.importorskip('cadquery')
    path,model=case(tmp_path,profile,points)
    model['expected'].update(volume_mm3=volume,bbox_mm=bbox);engine.dump(path,model)
    result=step_model.build(path,tmp_path/'output')
    assert result['properties_match'] and result['valid']
    assert 'polyline' in (tmp_path/'output/parametric.py').read_text()


def feature(identity,kind,x,y,depth,**shape):
    return {'id':identity,'type':kind,'dimensions':{k:dimension(v) for k,v in dict(x=x,y=y,depth=depth,**shape).items()}}


def test_through_blind_hole_and_rectangular_pocket(tmp_path):
    pytest.importorskip('cadquery')
    features=[feature('H1','through_hole',0,0,5,radius=1),feature('H2','blind_hole',5,0,2,radius=1),
              feature('P1','rectangular_pocket',-5,0,1,width=2,height=2)]
    path,model=case(tmp_path,'rectangle',features=features)
    model['expected'].update(volume_mm3=1000-7*math.pi-4,bbox_mm=[20,10,5]);engine.dump(path,model)
    result=step_model.build(path,tmp_path/'output')
    assert result['properties_match'] and result['solids']==1


@pytest.mark.parametrize('features',[
    [feature('H1','through_hole',9.9,0,5,radius=1)],
    [feature('H1','through_hole',0,0,5,radius=1),feature('H2','through_hole',0,0,5,radius=1)],
])
def test_clipped_and_overlapping_cuts_rejected(tmp_path,features):
    pytest.importorskip('cadquery')
    path,model=case(tmp_path,'rectangle',features=features)
    with pytest.raises(ValueError,match='Cut'):
        step_model.build(path,tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_self_intersecting_profile_and_missing_coordinate_evidence(tmp_path):
    path,model=case(tmp_path,'polygon',[(0,0),(10,10),(0,10),(10,0)])
    with pytest.raises(ValueError,match='intersect'):
        step_model.validate(path)
    model['vertices'][0]['x'].pop('statement');engine.dump(path,model)
    with pytest.raises(ValueError,match='evidence'):
        step_model.validate(path)
