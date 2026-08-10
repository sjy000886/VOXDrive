import sys
sys.path.append(
    "/home/dutsy/carla0.9.15_Binary/PythonAPI/carla/dist/carla-0.9.15-py3.8-linux-x86_64.egg"
)

import carla
import random
import time


# ==========================
# 连接CARLA
# ==========================

client = carla.Client(
    "localhost",
    2000
)

client.set_timeout(10.0)

world = client.get_world()

settings = world.get_settings()

print("====================")
print("同步模式:", settings.synchronous_mode)
print("固定步长:", settings.fixed_delta_seconds)
print("====================")


blueprints = world.get_blueprint_library()



# ==========================
# 获取Ego车辆
# ==========================

def get_ego():

    vehicles = world.get_actors().filter(
        "vehicle.*"
    )

    for v in vehicles:

        if v.attributes.get(
            "role_name"
        ) == "hero":

            return v

    return None



ego = None


while ego is None:

    print("等待Ego车辆...")

    ego = get_ego()

    world.wait_for_tick()



print(
    "Ego ID:",
    ego.id
)



# ==========================
# 加塞触发点
# ==========================

trigger_point = carla.Location(
    x=-906.7,
    y=-529,
    z=0
)


trigger_distance = 12



# ==========================
# 加塞车辆生成位置
# ==========================

# 假设：
# Ego车道 y=905
# 旁边车道 y=875


cutin_spawn = carla.Location(
    x=-910.3,
    y=-517.8,
    z=0.5
)



# ==========================
# 生成车辆
# ==========================

def spawn_vehicle():


    bp = random.choice(
        blueprints.filter(
            "vehicle.*"
        )
    )


    transform = carla.Transform(
        cutin_spawn,
        carla.Rotation(
            yaw=90
        )
    )


    vehicle = world.try_spawn_actor(
        bp,
        transform
    )


    if vehicle:

        print(
            "加塞车辆ID:",
            vehicle.id
        )


    else:

        print(
            "车辆生成失败"
        )


    return vehicle



# ==========================
# 车辆直行
# ==========================

def drive_forward(vehicle):


    vehicle.set_target_velocity(
        carla.Vector3D(
            x=0,
            y=12,
            z=0
        )
    )



# ==========================
# 执行加塞动作
# ==========================

def do_cut_in(vehicle):


    print(
        "开始加塞"
    )


    frames = 30


    # 横向移动距离一个车道宽度

    step = 3.6 / frames



    for i in range(frames):


        loc = vehicle.get_location()


        loc.x += step


        vehicle.set_transform(
            carla.Transform(
                loc,
                vehicle.get_transform().rotation
            )
        )


        world.wait_for_tick()



    print(
        "加塞完成"
    )



# ==========================
# 主循环
# ==========================


cutin_vehicle = None


triggered = False



while True:


    ego_loc = ego.get_location()


    distance = ego_loc.distance(
        trigger_point
    )


    print(
        "Ego距离:",
        round(distance,2)
    )


    if distance < trigger_distance and not triggered:


        triggered = True


        print("================")
        print("触发加塞")
        print("================")


        cutin_vehicle = spawn_vehicle()


        if cutin_vehicle:


            # 先直行3秒

            drive_forward(
                cutin_vehicle
            )


            start = time.time()


            while time.time()-start < 3:


                world.wait_for_tick()



            # 开始横向切入

            do_cut_in(
                cutin_vehicle
            )


            break



    world.wait_for_tick()



# ==========================
# 保留观察
# ==========================

print(
    "加塞结束，保持10秒"
)


for i in range(200):

    world.wait_for_tick()



# ==========================
# 删除
# ==========================


if cutin_vehicle:

    cutin_vehicle.destroy()


print(
    "车辆删除，结束"
)