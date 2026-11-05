import bpy, sys, json
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=argv[0])
out=[]
for o in bpy.data.objects:
    if o.type!='MESH': continue
    bb=[o.matrix_world @ Vector(c) for c in o.bound_box]
    mn=[min(v[i] for v in bb) for i in range(3)]; mx=[max(v[i] for v in bb) for i in range(3)]
    mats=[m.name for m in o.data.materials if m]
    col=None
    if o.data.materials and o.data.materials[0] and o.data.materials[0].node_tree:
        for n in o.data.materials[0].node_tree.nodes:
            if n.type=='BSDF_PRINCIPLED':
                col=[round(x,2) for x in n.inputs['Base Color'].default_value[:3]]
    out.append(dict(name=o.name, parent=o.parent.name if o.parent else None, min=[round(x,4) for x in mn], max=[round(x,4) for x in mx], verts=len(o.data.vertices), mats=mats, color=col))
with open(argv[1], 'w') as f:
    json.dump(out, f, indent=1)
print("MESHES", len(out))
