"""
处理：看到前方横穿马路的行人，减速避让后向左变道超越慢车
代码根据ego车辆到达trigger处时生成行人和前方慢车。
"""

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

client.set_timeout(10)


world = client.get_world()


settings = world.get_settings()


print("======================")
print("同步模式:",
      settings.synchronous_mode)

print("固定步长:",
      settings.fixed_delta_seconds)

print("======================")


blueprint_library = world.get_blueprint_library()





# ==========================
# 获取Ego
# ==========================


def get_ego_vehicle():


    vehicles = world.get_actors().filter(
        "vehicle.*"
    )


    for v in vehicles:


        if v.attributes.get(
            "role_name"
        ) == "hero":

            return v


    return None



ego_vehicle=None



while ego_vehicle is None:


    print(
        "等待Ego车辆..."
    )


    ego_vehicle=get_ego_vehicle()


    time.sleep(1)



print(
    "Ego ID:",
    ego_vehicle.id
)






# ==========================
# Trigger位置
# ==========================


trigger_point=carla.Location(

    x=-662.3,

    y=594.7,

    z=0

)


trigger_distance=10






# ==========================
# 行人参数
# ==========================


walker_spawn=carla.Location(

    x=-690.0,

    y=586.9,

    z=1.1

)

walker_speed=0.12

# ==========================
# 慢车参数
# ==========================


vehicle_spawn=carla.Location(

    x=-711.2,

    y=594.0,

    z=0.5

)



vehicle_rotation=carla.Rotation(

    yaw=180

)



vehicle_speed=25/3.6

# ==========================
# 生成行人
# ==========================


def spawn_walker():


    walker_bp=random.choice(

        blueprint_library.filter(

            "walker.pedestrian.*"

        )

    )



    walker=world.try_spawn_actor(

        walker_bp,

        carla.Transform(

            walker_spawn

        )

    )



    if walker is None:


        print(
            "行人生成失败"
        )


        return None



    print(

        "生成行人:",

        walker.id

    )



    # 手动控制

    walker.set_simulate_physics(

        False

    )



    return walker






# ==========================
# 生成慢车
# ==========================


def spawn_vehicle():


    vehicle_bp=random.choice(

        blueprint_library.filter(

            "vehicle.*"

        )

    )


    vehicle_bp.set_attribute(

        "role_name",

        "scenario_vehicle"

    )



    vehicle=world.try_spawn_actor(

        vehicle_bp,

        carla.Transform(

            vehicle_spawn,

            vehicle_rotation

        )

    )



    if vehicle is None:


        print(
            "车辆生成失败"
        )

        return None



    print(

        "生成车辆:",

        vehicle.id

    )



    vehicle.set_autopilot(
        False
    )



    vehicle.set_simulate_physics(
        False
    )


    return vehicle






# ==========================
# 等待触发
# ==========================


walker=None

npc_vehicle=None


while True:



    ego_location=ego_vehicle.get_location()



    distance=ego_location.distance(

        trigger_point

    )



    print(

        "Ego距离trigger:",

        round(distance,2)

    )



    if distance < trigger_distance:


        print("===================")

        print(
            "触发场景"
        )

        print("===================")



        walker=spawn_walker()


        npc_vehicle=spawn_vehicle()



        start_time=time.time()



        while time.time()-start_time < 40:



            # 不调用world.tick()
            # 防止影响MindDrive

            world.wait_for_tick()



            # ==================
            # 控制行人移动
            # ==================

            if walker:


                loc=walker.get_location()



                loc.y += walker_speed



                walker.set_location(

                    loc

                )



                print(

                    "行人:",

                    walker.get_location()

                )





            # ==================
            # 控制慢车
            # ==================


            if npc_vehicle:



                npc_vehicle.set_target_velocity(

                    carla.Vector3D(

                        x=-vehicle_speed,

                        y=0,

                        z=0

                    )

                )



                print(

                    "车辆:",

                    npc_vehicle.get_location()

                )



        break




    world.wait_for_tick()






# ==========================
# 删除
# ==========================


print(
    "删除场景参与者"
)



if walker:

    walker.destroy()



if npc_vehicle:

    npc_vehicle.destroy()



print(
    "结束"
)
