from modifier import *
import numpy as np

def ccrb_generalize(fname: str):
    distance_setting, skip = get_params("请依次输入自车与主车之间的最小初始距离，最大初始距离, 步进增量(m): ", 3)
    datum = ET.parse(os.path.join(PATH_, fname))
    root = datum.getroot()
    distances = [num for num in np.arange(float(distance_setting[0]),float(distance_setting[1]+distance_setting[2]),float(distance_setting[2]))]

    print(distances)
    # target_init_ypos = -80  # meters

    # 找GVT的ref
    gvt_id = root.find(AGENT_MODEL_XPATH).attrib['name']

    # 通过ref找到storyboard-init下拥有对应ref的private
    gvt_pos = root.find(INIT_PRIVATE_XPATH + f"[@entityRef='{gvt_id}']//WorldPosition")
    gvt_ypos = float(gvt_pos.attrib['y'])
    print(gvt_ypos)

    # 计算主车位置
    dis_compensation = -3.55 - 1.0              # 补偿前车后轴到后保和自车后轴到前保的距离
    for distance in distances:
        ego_init_pos = gvt_ypos - distance + dis_compensation
        change_ego_init_pos(datum, str(ego_init_pos))
        write_xosc(datum, fname.split('.')[0] + f"_dist{distance}.xosc")
    # 修改自车初始位置

    pass

def main():
    global NEW_FOLDER_NAME
    fnames = read_xosc()
    ccrb_generalize(fnames[0])
    NEW_FOLDER_NAME = '_'.join(["./", NEW_FOLDER_NAME])
    do_zip_compress(NEW_FOLDER_NAME)

if __name__ == "__main__":
    main()
    print("运行完毕┌(!￣◇￣)┘...")
    input("Press Enter to excit......")