import sys
sys.path.append(
    "/home/dutsy/carla0.9.15_Binary/PythonAPI/carla/dist/carla-0.9.15-py3.8-linux-x86_64.egg"
               )

import carla

client = carla.Client("localhost", 2000)
client.set_timeout(10)

world = client.get_world()

light_manager = world.get_lightmanager()

light_manager.set_day_night_cycle(False)

# 获取所有灯
lights = light_manager.get_all_lights()

print("路灯数量:", len(lights))

for light in lights:
    print(
        "ID:", light.id,
        "位置:", light.location
    )

# 打开所有灯
light_manager.turn_on(lights)
print("所有路灯已打开")

try:
    # 保持程序运行
    while True:
        world.wait_for_tick()

except KeyboardInterrupt:
    print("\n检测到 Ctrl+C，准备退出...")

finally:
    print("正在关闭所有路灯...")
    light_manager.turn_off(lights)
    print("所有路灯已关闭。")