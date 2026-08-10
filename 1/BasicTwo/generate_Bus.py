"""
公交车自动生成，在原地等待1分钟后行驶，运行1分钟后自动销毁；重复上述循环
"""

import sys
sys.path.append(
    "/home/dutsy/carla0.9.15_Binary/PythonAPI/carla/dist/carla-0.9.15-py3.8-linux-x86_64.egg"
               )
import carla
import time


client = carla.Client('localhost', 2000)
client.set_timeout(10)

world = client.get_world()

tm = client.get_trafficmanager(8000)


bp = world.get_blueprint_library().find(
    "vehicle.mitsubishi.fusorosa"
)


bus_data = [
    (carla.Location(x=-91.559, y=-14.8, z=0.8), 180),
    (carla.Location(x=-42.288, y=-14.8, z=0.8), 180),

    (carla.Location(x=121.204, y=9.55, z=0.8), 0),
    (carla.Location(x=172.188, y=9.7, z=0.8), 0),

    (carla.Location(x=990.5, y=187.698, z=0.8), 90),
    (carla.Location(x=990.5, y=255.868, z=0.8), 90),

    (carla.Location(x=1008.75, y=573.481, z=0.8), 270),
    (carla.Location(x=1008.75, y=656.282, z=0.8), 270),
]



# =============================
# 生成公交函数
# =============================

def spawn_buses():

    buses = []

    for i,(location,yaw) in enumerate(bus_data):

        transform = carla.Transform(
            location,
            carla.Rotation(
                yaw=yaw
            )
        )


        bus = world.try_spawn_actor(
            bp,
            transform
        )


        if bus:

            buses.append(bus)

            print(
                f"公交{i+1}生成 ID={bus.id}"
            )

    return buses



# =============================
# 删除公交函数
# =============================

def destroy_buses(buses):

    for bus in buses:

        if bus.is_alive:

            bus.destroy()

    print("公交全部删除")



# =============================
# 循环公交调度
# =============================

try:

    while True:


        # --------生成--------
        buses = spawn_buses()


        print(
            "公交开始停站等待60秒"
        )


        # --------停车阶段--------
        time.sleep(60)



        print(
            "公交开始运行"
        )


        # --------启动自动驾驶--------
        for bus in buses:

            if bus.is_alive:

                bus.set_autopilot(
                    True,
                    tm.get_port()
                )


        # --------运行60秒--------
        time.sleep(60)



        print(
            "运行结束，删除公交"
        )


        destroy_buses(buses)


        buses = []


        print(
            "等待下一轮生成"
        )


        time.sleep(5)



except KeyboardInterrupt:

    print(
        "用户中断程序"
    )


except Exception as e:

    print(
        "程序异常:",
        e
    )


finally:

    print(
        "清理剩余公交..."
    )


    for bus in buses:

        if bus.is_alive:

            bus.destroy()


    print(
        "清理完成"
    )