
import sys
sys.path.append(
    "/home/dutsy/carla0.9.15_Binary/PythonAPI/carla/dist/carla-0.9.15-py3.8-linux-x86_64.egg"
               )

import carla
import random
from collections import defaultdict


# =========================
# 连接 CARLA
# =========================

client = carla.Client("localhost", 2000)
client.set_timeout(10.0)

world = client.get_world()
carla_map = world.get_map()

tm = client.get_trafficmanager(8000)



# =========================
# 获取机动车 Blueprint
# =========================

blueprints = world.get_blueprint_library()

vehicle_bps = []


for bp in blueprints.filter("vehicle.*"):

    name = bp.id.lower()

    # 排除自行车
    if "bike" in name:
        continue

    vehicle_bps.append(bp)



print("================")
print("机动车模型数量:", len(vehicle_bps))

for bp in vehicle_bps:
    print(bp.id)



# =========================
# 获取道路Waypoint
# =========================

waypoints = carla_map.generate_waypoints(2.0)



# =========================
# 统计每条Road车道
# =========================

road_lanes = defaultdict(set)


for wp in waypoints:

    road_lanes[wp.road_id].add(
        wp.lane_id
    )



# =========================
# 筛选机动车生成点
# =========================

vehicle_waypoints = []


for wp in waypoints:


    lanes = road_lanes[wp.road_id]


    # ---------------------
    # 六车道
    # [-3,-2,-1,1,2,3]
    # ---------------------

    if lanes == {
        -3,-2,-1,
        1,2,3
    }:


        # 排除自行车道
        if wp.lane_id not in [-3,3]:

            vehicle_waypoints.append(wp)



    # ---------------------
    # 八车道
    # [-4,-3,-2,-1,1,2,3,4]
    # ---------------------

    elif lanes == {
        -4,-3,-2,-1,
        1,2,3,4
    }:


        # 排除自行车道
        if wp.lane_id not in [-4,4]:

            vehicle_waypoints.append(wp)



print("================")
print(
    "机动车可生成点:",
    len(vehicle_waypoints)
)



# =========================
# 生成机动车
# =========================

random.shuffle(vehicle_waypoints)


NUM_VEHICLES = 50


vehicles = []


for i in range(NUM_VEHICLES):


    # 随机选择车道位置
    wp = random.choice(
        vehicle_waypoints
    )


    # 随机车辆模型
    bp = random.choice(
        vehicle_bps
    )


    transform = wp.transform

    # 防止陷入路面
    transform.location.z += 0.3



    vehicle = world.try_spawn_actor(
        bp,
        transform
    )


    if vehicle:


        print(
            "生成:",
            vehicle.type_id,
            "Road:",
            wp.road_id,
            "Lane:",
            wp.lane_id
        )


        # =====================
        # Traffic Manager控制
        # =====================

        vehicle.set_autopilot(
            True,
            tm.get_port()
        )


        # 禁止主动变道
        tm.auto_lane_change(
            vehicle,
            False
        )


        vehicles.append(vehicle)



print("================")
print(
    "成功生成机动车:",
    len(vehicles)
)



# =========================
# 保持运行
# =========================

try:

    while True:

        world.wait_for_tick()



except KeyboardInterrupt:


    print("清理车辆")


    for v in vehicles:

        if v.is_alive:

            v.destroy()