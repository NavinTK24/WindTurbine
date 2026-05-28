import bpy
import math

# --- 1. CLEAN THE SCENE ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# --- 2. CREATE MATERIALS ---
def create_matte_material(name, color_rgb):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if 'Base Color' in bsdf.inputs:
            bsdf.inputs['Base Color'].default_value = color_rgb + (1.0,)
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = 0.35
    return mat

white_mat = create_matte_material("Fiberglass_White", (0.92, 0.92, 0.92))
gray_mat = create_matte_material("Galvanized_Steel", (0.35, 0.35, 0.35))

# --- 3. GENERATE THE TOWER ---
bpy.ops.mesh.primitive_cylinder_add(radius=0.8, depth=24, location=(0, 0, 12))
tower = bpy.context.object
tower.name = "Turbine_Tower"
tower.data.materials.append(gray_mat)
bpy.ops.object.shade_smooth()

# --- 4. GENERATE THE NACELLE (Engine Housing) ---
bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=4.0, location=(0, 0, 24.5))
nacelle = bpy.context.object
nacelle.name = "Nacelle"
nacelle.rotation_euler = (0, math.radians(90), 0)
nacelle.data.materials.append(white_mat)
bpy.ops.object.shade_smooth()

# --- 5. RIGGING: TWO-PART MECHANICAL AXIS (THE FIX) ---
# Node 1: The Tilt (This points the entire rotor assembly forward along the X-axis)
rotor_tilt = bpy.data.objects.new("Rotor_Tilt_Neck", None)
bpy.context.scene.collection.objects.link(rotor_tilt)
rotor_tilt.location = (2.0, 0, 24.5)
rotor_tilt.rotation_euler = (0, math.radians(90), 0)

# Node 2: The Spin (This is a child of the Tilt node. Its rotation is purely local)
rotor_spin = bpy.data.objects.new("Rotor_Spin_Bearing", None)
bpy.context.scene.collection.objects.link(rotor_spin)
rotor_spin.parent = rotor_tilt
rotor_spin.location = (0, 0, 0)
rotor_spin.rotation_euler = (0, 0, 0) 

# --- 6. GENERATE THE FLOATING ROTOR HUB ---
bpy.ops.mesh.primitive_cone_add(radius1=1.1, radius2=0, depth=2.5)
hub = bpy.context.object
hub.name = "Rotor_Hub"
hub.parent = rotor_spin  # Parented directly to the spinning bearing
hub.location = (0, 0, 1.25)
hub.rotation_euler = (0, 0, 0)
hub.data.materials.append(white_mat)
bpy.ops.object.shade_smooth()

# --- 7. NACA 4412 AIRFOIL MATHEMATICAL GENERATOR ---
def generate_naca4412_profile(samples=12):
    m = 0.04
    p = 0.4
    t = 0.12
    
    profile_points = []
    
    # Upper Surface
    for i in range(samples + 1):
        x = i / samples
        yt = 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * (x**2) + 0.2843 * (x**3) - 0.1015 * (x**4))
        yc = (m / (p**2)) * (2*p*x - x**2) if x < p else (m / ((1-p)**2)) * ((1-2*p) + 2*p*x - x**2)
        dyc = (2 * m / (p**2)) * (p - x) if x < p else (2 * m / ((1-p)**2)) * (p - x)
        theta = math.atan(dyc)
        
        xu = x - yt * math.sin(theta)
        yu = yc + yt * math.cos(theta)
        profile_points.append((xu, yu))
        
    # Lower Surface
    for i in range(samples - 1, 0, -1):
        x = i / samples
        yt = 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * (x**2) + 0.2843 * (x**3) - 0.1015 * (x**4))
        yc = (m / (p**2)) * (2*p*x - x**2) if x < p else (m / ((1-p)**2)) * ((1-2*p) + 2*p*x - x**2)
        dyc = (2 * m / (p**2)) * (p - x) if x < p else (2 * m / ((1-p)**2)) * (p - x)
        theta = math.atan(dyc)
        
        xl = x + yt * math.sin(theta)
        yl = yc - yt * math.cos(theta)
        profile_points.append((xl, yl))
        
    return profile_points

# --- 8. BUILD AND DISTRIBUTE BLADES IN ROTATION PLANE ---
def build_naca_blade(name, parent_control, index):
    radial_angle = math.radians(index * 120)
    
    blade_root = bpy.data.objects.new(f"Blade_Anchor_{index}", None)
    bpy.context.scene.collection.objects.link(blade_root)
    blade_root.parent = parent_control
    
    blade_root.location = (0, 0, 0.4)
    blade_root.rotation_euler = (0, 0, radial_angle)
    
    verts = []
    faces = []
    sections = 15
    blade_length = 9.5
    samples_per_side = 12
    num_pts = 2 * samples_per_side
    
    naca_base_profile = generate_naca4412_profile(samples_per_side)
    
    for s in range(sections):
        t_span = s / (sections - 1)
        dist = t_span * blade_length
        
        chord_width = 1.2 * (1.0 - 0.75 * t_span)
        twist = math.radians(22 * (1.0 - t_span))  
        
        for x_naca, y_naca in naca_base_profile:
            cx = (x_naca - 0.25) * chord_width
            cy = y_naca * chord_width
            
            x_local = cx
            z_local = cy
            
            x_rot = x_local * math.cos(twist) - z_local * math.sin(twist)
            z_rot = x_local * math.sin(twist) + z_local * math.cos(twist)
            
            verts.append((x_rot, dist, z_rot))
            
        if s > 0:
            base = (s - 1) * num_pts
            for v in range(num_pts):
                v1 = base + v
                v2 = base + ((v + 1) % num_pts)
                v3 = base + num_pts + ((v + 1) % num_pts)
                v4 = base + num_pts + v
                faces.append([v1, v2, v3, v4])
                
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    
    obj.parent = blade_root
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)
    obj.data.materials.append(white_mat)
    
    for poly in obj.data.polygons:
        poly.use_smooth = True

# Parent the blades to the spinning bearing
for i in range(3):
    build_naca_blade(f"NACA_Blade_{i}", rotor_spin, i)

# --- 9. ANIMATION ENGINE (DRIVE THE BEARING ONLY) ---
# Because we drive the child bearing, the Euler math is clean. It spins around its local forward axis.
driver = rotor_spin.driver_add("rotation_euler", 2).driver
driver.expression = "frame * -0.08" # Negative value ensures it rotates clockwise into the wind

bpy.context.scene.frame_end = 250
print("Turbine Axis Rigged and Spinning Correctly!")