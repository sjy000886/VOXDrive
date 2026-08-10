
import sys
sys.path.append(
    "/home/dutsy/carla0.9.15_Binary/PythonAPI/carla/dist/carla-0.9.15-py3.8-linux-x86_64.egg"
               )

import carla
import random
from collections import defaultdict


# ==========================
# 连接 CARLA
# ==========================

client = carla.Client("localhost", 2000)
client.set_timeout(10.0)

world = client.get_world()
carla_map = world.get_map()

tm = client.get_trafficmanager(8000)
tm.set_synchronous_mode(False)


# ==========================
# 获取自行车 blueprint
# ==========================

blueprints = world.get_blueprint_library()

bike_bps = blueprints.filter("vehicle.*")

bike_list = []

for bp in bike_bps:
    if "bike" in bp.id:
        bike_list.append(bp)


if len(bike_list) == 0:
    raise RuntimeError("没有找到自行车，请检查blueprint")

print("找到自行车:")
for bp in bike_list:
    print(bp.id)


bike_bp = random.choice(bike_list)

print("使用:")
print(bike_bp.id)



# ==========================
# 获取道路Waypoint
# ==========================

waypoints = carla_map.generate_waypoints(2.0)



# ==========================
# 统计每条road的lane
# ==========================

road_lanes = defaultdict(set)


for wp in waypoints:

    road_lanes[wp.road_id].add(
        wp.lane_id
    )



# ==========================
# 找自行车生成位置
# ==========================

bike_waypoints = []


for wp in waypoints:

    lanes = road_lanes[wp.road_id]


    # 六车道道路
    if lanes == {
        -3,-2,-1,
        1,2,3
    }:

        if wp.lane_id in [-3,3]:
            bike_waypoints.append(wp)



    # 八车道道路
    elif lanes == {
        -4,-3,-2,-1,
        1,2,3,4
    }:

        if wp.lane_id in [-4,4]:
            bike_waypoints.append(wp)



print(
    "可生成自行车点:",
    len(bike_waypoints)
)



# ==========================
# 生成自行车
# ==========================

random.shuffle(bike_waypoints)


NUM_BIKES = 40

bikes=[]


for wp in bike_waypoints:


    if len(bikes)>=NUM_BIKES:
        break


    transform = wp.transform


    # 防止陷入地面
    transform.location.z += 0.3


    bike = world.try_spawn_actor(
        bike_bp,
        transform
    )


    if bike:

        print(
            "生成:",
            bike.id,
            "lane:",
            wp.lane_id,
            "road:",
            wp.road_id
        )


        # 开启自动驾驶
        bike.set_autopilot(
            True,
            tm.get_port()
        )


        # 调整速度
        tm.vehicle_percentage_speed_difference(
            bike,
            30
        )


        bikes.append(bike)



print(
    "成功生成自行车:",
    len(bikes)
)



# ==========================
# 保持运行
# ==========================

try:

    while True:

        world.wait_for_tick()


except KeyboardInterrupt:


    print("删除自行车")


    for bike in bikes:

        if bike.is_alive:
            bike.destroy()