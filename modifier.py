'''
Author: Haihui Miao
Date: 2023/2/1
Last Updated: 2023/2/6
Python version: 3.8.15
Purpose: 批量修改或创建OpenScenario文件 (基于OpenScenario 1.4测试)
Comment: 主车替换功能不完备(无从获取主车的某些参数, 包括Bounding Box, maxAcceleration等), 建议还是用51进行替换。
'''
import xml.etree.ElementTree as ET
import glob
import json
import os

INIT_PRIVATE_XPATH = "./Storyboard/Init/Actions/Private"
EGO_INIT_VEL_XPATH = INIT_PRIVATE_XPATH + "//LongitudinalAction//AbsoluteTargetSpeed"
GVT_INIT_POS_XPATH = "./Storyboard/Init/Actions/Private/"
STOP_TRIGGER_XPATH = ".//StopTrigger//SimulationTimeCondition"
EGO_MODEL_XPATH = ".//Entities/ScenarioObject[@name='Ego']"
EGO_NAME_XPATH = EGO_MODEL_XPATH + "/Vehicle"
EGO_CONTROLLER_XPATH = EGO_MODEL_XPATH + "/ObjectController"
EGO_PROPERTIES_XPATH = EGO_NAME_XPATH + "/Properties"
AGENT_MODEL_XPATH = ".//Entities/ScenarioObject[2]"     # 假设对手目标是第二个scenarioObject
AGENT_NAME_XPATH = AGENT_MODEL_XPATH + "/Vehicle"
AGENT_PROPERTIES_XPATH = AGENT_NAME_XPATH + "/Properties"
AGENT_BOUNDINGBOX_XPATH = AGENT_NAME_XPATH + "/BoundingBox"
NEW_FOLDER_NAME = "./new"

# 批量读取xosc文件名
# 返回包含文件名的list
def read_xosc():
    files_name = [filename for filename in os.listdir("./") if "xosc" in filename ]
    print (f"一共读取到{len(files_name)}个xosc文件\n读取到的xosc文件: {files_name}")
    return files_name

# 创建一个新文件夹，并把结果存放进去
def write_xosc(tree: ET.ElementTree, name):
    if not os.path.exists(NEW_FOLDER_NAME):
        os.mkdir(NEW_FOLDER_NAME)
    # 将新xosc写入指定文件中
    tree.write(f"{NEW_FOLDER_NAME}/{name}",encoding="UTF-8",xml_declaration=True,method="xml")
    print(f"已将更新后的 [{name}] 保存至路径 {NEW_FOLDER_NAME}")

# 修改主车初速度
def change_ego_init_velocity(tree: ET.ElementTree, target_speed):

    OpenSCENARIO = tree.getroot()
    Ego_init_vel = OpenSCENARIO.find(EGO_INIT_VEL_XPATH)
    Ego_init_vel.set('value', target_speed)
    # print(Ego_init_vel.attrib)
    return tree

# 根据偏置率修改对手车横坐标
def change_gvt_init_pos(tree: ET.ElementTree, overlap: float, gvt_width: float):

    root = tree.getroot()
    gvt = root.find(AGENT_MODEL_XPATH)
    gvt_ref = gvt.attrib['name']
    world_position = root.find(f"{INIT_PRIVATE_XPATH}[@entityRef='{gvt_ref}']//WorldPosition")
    # 假设基准案例的偏置率是100%，获取对手车坐标
    datum_pos = float(world_position.attrib['x'])
    world_position.set('x',str(datum_pos-overlap*gvt_width))
    return tree

# 修改场景结束触发器
def change_end_trigger(tree: ET.ElementTree, terminate_trigger_time):
    OpenSCENARIO = tree.getroot()
    terminate_trigger = OpenSCENARIO.find(STOP_TRIGGER_XPATH)
    terminate_trigger.set('value', terminate_trigger_time)
    return tree

# 修改主车模型，不建议用，无从获知boundingBox信息
# 建议将场景导出51后，再在导入时批量修改主车模型
def change_ego(tree: ET.ElementTree):
    # 读取模型JSON文件
    model_file = [filename for filename in os.listdir("./") if "json" in filename ]
    try:
        model_file.remove('agents.json')
    except:
        pass
    with open(f"./{model_file[0]}",'r') as fp:
        vmodel = json.load(fp)
    # TODO JSON文件中没有BoundingBox的相关信息，暂时不知道对仿真的影响(推测会影响真值GT获取)。可能需要手动填写
    # 获取主车的元素
    OpenSCENARIO = tree.getroot()
    name_element = OpenSCENARIO.find(EGO_NAME_XPATH)
    properties_element = OpenSCENARIO.find(EGO_PROPERTIES_XPATH)
    controller_element = OpenSCENARIO.find(EGO_CONTROLLER_XPATH)
    
    # 写入新主车模型的参数
    name_element.set('name',vmodel['id'])
    properties_element.find("./Property[@name='model']").set('value',vmodel['id'])
    properties_element.find("./Property[@name='name']").set('value',vmodel['name'])
    controller_element.find("./Controller").set('name',vmodel['controller']['name'])
    controller_element.find("./Controller/Properties/Property").set('value',vmodel['controller']['name'])
    return tree

# 修改对手车模型
def change_gvt(tree: ET.ElementTree, new_agent: str):
    # 读取模型JSON文件
    try:
        with open(f"./agents.json",'r') as fp:
            agent_dict = json.load(fp)
    except OSError:
        print("Error: 当前目录下没有agents.json\n程序终止...")
        input('Press Enter to exit...')
        exit()
    agents = agent_dict['agent_type']
    agent_name = [agent for agent in agents.keys() if new_agent in agent]
    if len(agent_name) > 1:
        print("Error: 输入的对手车的名字匹配到复数目标, 请输入更精准的名字\n程序终止...")
        input('Press Enter to exit...')
        exit()
    elif len(agent_name) == 0:
        print("Error: 没有匹配的车型, 请输入正确的名字\n程序终止...")
        input('Press Enter to exit...')
        exit()
    agent_name = agent_name[0]
    agent = agents[agent_name]
    
    # 获取对手车的元素
    OpenSCENARIO = tree.getroot()
    name_element = OpenSCENARIO.find(AGENT_NAME_XPATH)
    properties_element = OpenSCENARIO.find(AGENT_PROPERTIES_XPATH)
    bounding_box_element = OpenSCENARIO.find(AGENT_BOUNDINGBOX_XPATH)
    dimension_element = bounding_box_element.find("./Dimensions")
    # 写入新对手车的参数
    name_element.set('name',agent_name)
    name_element.set('vehicleCategory',agent['subCategory'].lower())
    dimension_element.set('height', str(float(agent['height'])/100))
    dimension_element.set('length', str(float(agent['length'])/100))
    dimension_element.set('width', str(float(agent['width'])/100))
    properties_element.find("./Property[@name='model']").set('value',agent_name)
    properties_element.find("./Property[@name='name']").set('value',new_agent)
    properties_element.find("./Property[@name='category']").set('value',agent['category'].lower())
    return tree

# 获取指定数量的输入
def get_params(info: str, number_of_params = 3):
    skip = True
    params = (input (info)).split(' ')

    while len(params) != number_of_params and not (len(params)==1 and params[0]==''):
        print("输入的参数数量不正确, 请重新输入")
        params = (input (info)).split(' ')
    if '' not in params and len(params) == number_of_params:
        skip = False
        params = [float(param) for param in params]
    return params, skip

# 基于基准场景生成新场景的名字
def generate_scenario_name(datum: str, speed: str, overlap_rate: str=None):
    filename = datum.partition('.xosc')[0]
    casename = datum.split('_')
    if speed != None:
        index = [i for i, j in enumerate(casename) if 'speed' in j]
        casename[index[0]] = 'speed'+ speed
    if overlap_rate != None:
        # change the raw overlap rate to specific name
        if float(overlap_rate) > 0:
            overlap_name = str(100 - overlap_rate * 100)
        elif float(overlap_rate) < 0:
            overlap_name = str(-100 - overlap_rate * 100)
        else:
            overlap_name = '100'
        # update the file name
        index = [i for i, j in enumerate(casename) if '%' in j]
        casename[index[0]] = overlap_name + '%'
    return '_'.join(casename) + '.xosc'

# 批量修改模块
def batch_modify(fnames):
    # 获取参数
    print("批量修改功能已启动~")
    print("接下来请输入需要统一修改的参数的值，不输入则默认为不修改")
    speed = input ("需要将速度修改为(km/h): ")
    end_trigger_time = input ("需要将结束触发器设置为(s): ")
    gvt = input("需要将对手车模型修改为(输入agents.json下的任意车型): ")
    ego = input("是否更改主车模型为当前目录下的模型？(y/n): ")
    print("\n")

    # 依次将需要修改的参数写入树中
    for fname in fnames:
        tree = ET.parse(fname)
        if len(speed) != 0:
            fname = generate_scenario_name(fname,speed) 
            speed = str(float(speed)/3.6)
            tree = change_ego_init_velocity(tree, speed)
        if len(end_trigger_time) != 0:
            tree = change_end_trigger(tree, end_trigger_time)
        if ego == 'y' or ego == 'Y':
            tree = change_ego(tree)
        if len(gvt) != 0:
            tree = change_gvt(tree,gvt)
        write_xosc(tree, fname)

# 泛化模块
def generalize(base):
    print("泛化功能已启动~")
    print("接下来请输入需要统一修改的参数的值，不输入则默认为不泛化\n======每个输入间请以空格隔开======")
    speed_settings, skip_speed = get_params("请依次输入最低主车速度，最高主车速度，步进增量(km/h): ")
    
    overlap_settings, skip_overlap = get_params("(仅限C2C场景)请依次输入最低偏置率，最高偏置率, 步进增量(%), 对手车车宽(m): ", 4)

    datum = ET.parse(base)
    root = datum.getroot()
    datum_vel = root.find(EGO_INIT_VEL_XPATH)
    if skip_speed:
        speeds = datum_vel.attrib['value']
    else:
        speeds = [str(num/3.6) for num in range(int(speed_settings[0]),int(speed_settings[1]+1),int(speed_settings[2]))]
    if skip_overlap:
        overlaps = [0]
    else:
        overlaps = [num/100.0 for num in range(int(overlap_settings[0]),int(overlap_settings[1]+1),int(overlap_settings[2]))] 
    # 逐项泛化
    for speed in speeds:
        for overlap in overlaps:   
            change_ego_init_velocity(datum, speed)
            # write_xosc(datum, generate_scenario_name(base,speed=str(float(speed)*3.6)))
            if not skip_overlap:
                change_gvt_init_pos(datum, overlap, overlap_settings[3])
                write_xosc(datum, generate_scenario_name(base,speed=str(int(float(speed)*3.6)), overlap_rate=str(overlap)))
            else:
                write_xosc(datum, generate_scenario_name(base,speed=str(int(float(speed)*3.6))))
        pass

def main():
    # change_ego_init_velocity()
    fnames = read_xosc()
    option = input("批量修改请按1, 泛化请按2: ")
    print("\n")
    if option == "1":
        batch_modify(fnames)
    elif option == "2":
        generalize(fnames[0])

if __name__ == "__main__":
    
    print("温馨提示: 使用该脚本前, 请确保脚本所在文件目录下的所有xosc文件都是需要被修改的! \n如需修改主车模型, 请将对应的JSON文件放置在当前目录下:)\n如需修改对手车模型, 请将agents.json文件放置在当前目录。该文件可以在51simone的安装目录下/Module/VehicleDynamics/obstacle下找到:3")
    main()
    print("运行完毕┌(!￣◇￣)┘...")
    input("Press Enter to excit......")