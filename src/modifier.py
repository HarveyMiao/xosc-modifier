'''
Author: Haihui Miao
Date: 2023/2/1
Last Updated: 2023/2/6
Python version: 3.8.15
Purpose: 批量修改或创建OpenScenario文件 (基于OpenScenario 1.4测试)
Comment: 主车替换功能不完备(无从获取主车的某些参数, 包括Bounding Box, maxAcceleration等), 建议还是用51进行替换。
'''
import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
# print(os.getcwd())

import xml.etree.ElementTree as ET
from itertools import product as cartesianProduct
import json
import zipfile
import platform
from global_var import *

INIT_PRIVATE_XPATH = "./Storyboard/Init/Actions/Private"
EGO_INIT_VEL_XPATH = INIT_PRIVATE_XPATH + "//LongitudinalAction//AbsoluteTargetSpeed"
EGO_INIT_POS_XPATH = INIT_PRIVATE_XPATH + "[@entityRef='Ego']//WorldPosition"
STOP_TRIGGER_XPATH = ".//StopTrigger//SimulationTimeCondition"
EGO_MODEL_XPATH = ".//Entities/ScenarioObject[@name='Ego']"
EGO_NAME_XPATH = EGO_MODEL_XPATH + "/Vehicle"
EGO_CONTROLLER_XPATH = EGO_MODEL_XPATH + "/ObjectController"
EGO_PROPERTIES_XPATH = EGO_NAME_XPATH + "/Properties"
AGENT_MODEL_XPATH = ".//Entities/ScenarioObject[2]"                     # 假设对手目标是第二个scenarioObject
AGENT_NAME_XPATH = AGENT_MODEL_XPATH + "/Vehicle"
AGENT_PROPERTIES_XPATH = AGENT_NAME_XPATH + "/Properties"
AGENT_BOUNDINGBOX_XPATH = AGENT_NAME_XPATH + "/BoundingBox"
INIT_NEW_FOLDER_NAME = "new"                                            # 可以更改为更有意义的名字，改名字或作为新建文件夹的后缀
NEW_FOLDER_NAME = INIT_NEW_FOLDER_NAME
PATH_ = "./"
OVERLAP_COUNT = 0

class JSON_Loader:
    def __init__(self, dirpath="./") -> None:
        try:
            print("读取config.json中...")
            with open(os.path.join(dirpath, "config.json"), "+r", encoding="utf-8") as fp:
                self.__config = json.load(fp)
                print("读取完毕")
        except OSError as e:
            print(f"无法打开config.json: {e}")
            print("启用手动输入模式")
            self.__config = {"auto_mode": False}
    @property
    def config(self):
        return self.__config
    
def set_new_folder_suffix(name):
    '''
    修改放置新的xosc文件的文件夹
    '''
    global INIT_NEW_FOLDER_NAME
    INIT_NEW_FOLDER_NAME = name if len(name) != 0 else "new"

def overlap_count():
    global OVERLAP_COUNT
    OVERLAP_COUNT = OVERLAP_COUNT + 1
    return OVERLAP_COUNT

def set_new_folder_name(dirpath='./', addition=None):
    global NEW_FOLDER_NAME
    if addition == None:
        NEW_FOLDER_NAME = '_'.join([dirpath, INIT_NEW_FOLDER_NAME])
    else:
        NEW_FOLDER_NAME = '_'.join([dirpath + addition, INIT_NEW_FOLDER_NAME])

def read_xosc(dirpath='./', strict=False):
    '''
    批量读取xosc文件名
    @param dirpath: 文件路径，默认值为./
    @oaram strict: 如果是True, 则在读取不到xosc时报错
    @return 包含xosc文件名的list
    '''
    global PATH_
    # global NEW_FOLDER_NAME    

    # dirpath = input("请输入xosc所在的文件夹路径: ")
    # PATH_ = dirpath if dirpath != "" else "./"
    PATH_ = dirpath
    # NEW_FOLDER_NAME = '_'.join([dirpath, INIT_NEW_FOLDER_NAME])

    print(f"正在读取{dirpath}下的xosc...")
    files_name = [filename for filename in os.listdir(PATH_) if "xosc" in filename ]
    print (f"一共读取到{len(files_name)}个xosc文件\n读取到的xosc文件: {files_name}")
    if strict == True and len(files_name) == 0:
        raise FileExistsError(f"at least one xosc required")
    return files_name

# 创建一个新文件夹，并把结果存放进去
def write_xosc(tree: ET.ElementTree, name):
    '''
    创建新文件夹, 并把xml写入进去
    @param tree: 当前的ElementTree实例
    @param name: 案例名
    '''
    if not os.path.exists(NEW_FOLDER_NAME):
        os.mkdir(NEW_FOLDER_NAME)
    # 将新xosc写入指定文件中
    tree.write(f"{NEW_FOLDER_NAME}/{name}",encoding="UTF-8",xml_declaration=True,method="xml")
    print(f"已将更新后的 [{name}] 保存至路径 {NEW_FOLDER_NAME}")

def change_ego_init_velocity(tree: ET.ElementTree, target_speed) -> ET.ElementTree:
    '''
    修改主车初速度
    @param tree: 基准场景的ElementTree
    @param target_speed:
    @return tree: 修改后的ElementTree
    '''
    OpenSCENARIO = tree.getroot()
    Ego_init_vel = OpenSCENARIO.find(EGO_INIT_VEL_XPATH)
    Ego_init_vel.set('value', target_speed)
    # print(Ego_init_vel.attrib)
    return tree

def change_ego_init_pos(tree: ET.ElementTree, target_pos: str):
    '''
    修改主车初始y轴位置
    @param tree: 基准场景的ElementTree
    @param target_pos:
    @return tree: 修改后的ElementTree
    '''
    OpenSCENARIO = tree.getroot()
    Ego_init_vel = OpenSCENARIO.find(EGO_INIT_POS_XPATH)
    Ego_init_vel.set('y', target_pos)
    # print(Ego_init_vel.attrib)
    return tree

def change_gvt_init_pos(tree: ET.ElementTree, overlap: float, gvt_width: float):
    '''
    根据偏置率修改对手车横坐标
    @param tree: 基准场景的ElementTree
    @param overlap: 偏置率
    @param gvt_width: 主车宽度
    @return tree: 修改后的ElementTree
    '''
    root = tree.getroot()
    gvt = root.find(AGENT_MODEL_XPATH)
    gvt_ref = gvt.attrib['name']
    world_position = root.find(f"{INIT_PRIVATE_XPATH}[@entityRef='{gvt_ref}']//WorldPosition")
    # 假设基准案例的偏置率是100%，获取对手车坐标
    datum_pos = float(world_position.attrib['x'])
    world_position.set('x',str(datum_pos-overlap*gvt_width))
    return tree

def change_end_trigger(tree: ET.ElementTree, terminate_trigger_time):
    '''
    修改场景结束时间
    @param tree: 原场景的ElementTree
    @param terminate_trigger_time: 修改后的结束时间
    @return tree: 修改后的ElementTree
    '''
    OpenSCENARIO = tree.getroot()
    terminate_trigger = OpenSCENARIO.find(STOP_TRIGGER_XPATH)
    terminate_trigger.set('value', terminate_trigger_time)
    return tree

# 修改主车模型，不建议用，无从获知boundingBox信息
# 建议将场景导出51后，再在导入时批量修改主车模型
def change_ego(tree: ET.ElementTree, ego_name, dirpath="./"):
    '''
    修改主车模型\n
    不建议用, 无从获知boundingBox信息。
    建议将场景导出51后, 再在导入时批量修改主车模型
    @param tree: 原场景的ElementTree
    @param ego_name: 主车模型的名字
    @return tree: 修改后的ElementTree
    '''
    # 读取模型JSON文件
    # model_file = [filename for filename in os.listdir(dirpath) if "json" in filename ]
    # if 'agents.json' in model_file:
    #     model_file.remove('agents.json')
    # if 'config.json' in model_file:
    #     model_file.remove('config.json')
    
    model_file = [filename for filename in os.listdir(dirpath) if ("json" in filename and ego_name in filename) ]
    if len(model_file) > 1:
        print("Error: 输入的主车的名字匹配到复数目标, 请输入更精准的名字\n程序终止...")
        input('Press Enter to exit...')
        exit()
    elif len(model_file) == 0:
        print("Error: 没有匹配的主车json文件, 请输入正确的名字\n程序终止...")
        input('Press Enter to exit...')
        exit()

    with open(os.path.join(dirpath, f"{model_file[0]}"),'r', encoding='utf-8') as fp:
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
    # controller_element.find("./Controller").set('name',vmodel['controller']['name'])
    # controller_element.find("./Controller/Properties/Property").set('value',vmodel['controller']['name'])
    return tree

def change_gvt(tree: ET.ElementTree, new_agent: str, dirpath="./"):
    '''
    修改对手车模型
    @param tree: 原场景的ElementTree
    @param new_agent: 新对手车的名字
    @return tree: 修改后的ElementTree
    '''
    # 读取模型JSON文件
    try:
        with open(os.path.join(dirpath, "agents.json"),'r',encoding='utf-8') as fp:
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

def get_params(info: str, number_of_params = 3):
    '''
    获取指定数量的输入
    @param info: 输出的信息
    @param number_of_params: 输入的数量
    @return params: 获取的输入的列表
    @return skip: 是否有输入
    '''
    skip = True
    params = (input (info)).split(' ')

    while len(params) != number_of_params and not (len(params)==1 and params[0]==''):
        print("输入的参数数量不正确, 请重新输入")
        params = (input (info)).split(' ')
    if '' not in params and len(params) == number_of_params:
        skip = False
        params = [float(param) for param in params]
    return params, skip

def load_params(input_: dict, number_of_params = 3):
    '''
    从dict中获取指定数量的输入
    @param info: 输入的dict
    @param number_of_params: 输入的数量
    @return params: 获取的输入的列表
    @return skip: 是否有正确数量的输入
    '''
    skip = True
    params = []
    count = 0
    for _, param in input_.items():
        if param != "":
            params.append(float(param))
            count = count + 1
    if count > 0 and count != number_of_params:
        raise ValueError("Not enough input parameters")
    elif count == number_of_params:
        skip = False
    return params, skip

# 基于基准场景生成新场景的名字
def generate_scenario_name(datum: str, speed: str, overlap_rate: str=None):
    filename = datum.partition('.xosc')[0]
    casename = filename.split('_')
    if speed != None:
        index = [i for i, j in enumerate(casename) if 'speed' in j]
        casename[index[0]] = 'speed'+ speed
    if overlap_rate != None:
        # change the raw overlap rate to specific name
        if float(overlap_rate) > 0:
            overlap_name = "+" + str(round(100 - float(overlap_rate) * 100))
        elif float(overlap_rate) < 0:
            overlap_name = str(round(-100 - float(overlap_rate) * 100))
        else:
            overlap_name = '+100'
        # update the file name
        index = [i for i, j in enumerate(casename) if '%' in j]
        if len(index) != 0:
            casename[index[0]] = overlap_name + '%'
        else:
            index = [i for i, j in enumerate(casename) if 'speed' in j]
            casename.insert(index[0] + 1, overlap_name + '%')
    return '_'.join(casename) + '.xosc'

# 批量修改模块
class Batch_modifier:
    def __init__(self) -> None:
        print("批量修改功能已启动~")
        print("接下来请输入需要统一修改的参数的值，不输入则默认为不修改")
        self.gvt_path = input("agents.json的文件路径")
        self.ego_path = input("主车JSON的文件路径")
        self.speed = input ("需要将速度修改为(km/h): ")
        self.end_trigger_time = input ("需要将结束触发器设置为(s): ")
        self.gvt = input("需要将对手车模型修改为(输入agents.json下的任意车型): ")
        self.ego = input("是否更改主车模型为当前目录下的模型？(y/n): ")
        # self.change_ego = True if (self.ego == 'y' or self.ego == 'Y') else False
        self.change_ego = False if self.ego == "" else True

    def __init__(self, config: dict) -> None:
        print("批量修改功能已启动~")
        self.speed = config['batch_modify_params']['speed']
        self.end_trigger_time = config['batch_modify_params']['end_trigger_time']
        self.gvt = config['batch_modify_params']['gvt_name']
        self.gvt_path = config['batch_modify_params']['gvt_path']
        self.ego_path = config['batch_modify_params']['ego_path']
        self.ego = config['batch_modify_params']['ego']
        # self.change_ego = True if (self.ego == 'y' or self.ego == 'Y') else False
        self.change_ego = False if self.ego == "" else True

        if len(self.speed) != 0: 
            print(f"速度将被修改为{self.speed} km/h")
        if len(self.end_trigger_time) != 0: 
            print(f"场景结束时间将被修改为{self.end_trigger_time} s")
        if self.change_ego:
            print(f"主车将被修改")
        if len(self.gvt) != 0:
            print(f"对手车将被修改为{self.gvt}")

    def batch_modify(self, fnames):
        # 依次将需要修改的参数写入树中
        for fname in fnames:
            # tree = ET.parse(fname)
            tree = ET.parse(os.path.join(PATH_,fname))
            if len(self.speed) != 0: 
                fname = generate_scenario_name(fname, self.speed)
                # fname = generate_scenario_name(fname, "30")
                speedm = str(float(self.speed)/3.6)
                tree = change_ego_init_velocity(tree, speedm)
            if len(self.end_trigger_time) != 0:
                tree = change_end_trigger(tree, self.end_trigger_time)
            if self.ego:
                tree = change_ego(tree, self.ego, self.ego_path)
            if len(self.gvt) != 0:
                tree = change_gvt(tree,self.gvt, self.gvt_path)
            write_xosc(tree, fname)

# 泛化模块
def generalize(base):
    global CONFIG
    print("泛化功能已启动~")
    if CONFIG.config["auto_mode"]:
        speed_settings, skip_speed = load_params(CONFIG.config["generalize_params"]["speed_gen"], 3)
        overlap_settings, skip_overlap = load_params(CONFIG.config["generalize_params"]["overlap_gen"], 4)
    else:
        print("接下来请输入需要统一修改的参数的值，不输入则默认为不泛化\n======每个输入间请以空格隔开======")
        speed_settings, skip_speed = get_params("请依次输入最低主车速度，最高主车速度，步进增量(km/h): ")
        
        overlap_settings, skip_overlap = get_params("(仅限C2C场景)请依次输入最低偏置率，最高偏置率, 步进增量(%), 对手车车宽(m): ", 4)

    datum = ET.parse(os.path.join(PATH_,base))
    root = datum.getroot()
    datum_vel = root.find(EGO_INIT_VEL_XPATH)
    if skip_speed:
        speeds = [datum_vel.attrib['value']]
    else:
        speeds = []
        speeds = [str(num/3.6) for num in range(int(speed_settings[0]),int(speed_settings[1])+int(speed_settings[2]),int(speed_settings[2]))]
    if skip_overlap:
        overlaps = [0]
    else:
        overlaps = [num/100.0 for num in range(int(overlap_settings[0]),int(overlap_settings[1])+1,int(overlap_settings[2]))] 
    
    # 逐项泛化
    params_set = list(cartesianProduct(speeds,overlaps))
    for params in params_set:
        speed = params[0]
        overlap = params[1]
        # print(f"({speed}, {overlap})")
        change_ego_init_velocity(datum, speed)
        if not skip_overlap:
            change_gvt_init_pos(datum, overlap, overlap_settings[3])
            write_xosc(datum, generate_scenario_name(base,speed=str(round(float(speed)*3.6)), overlap_rate=str(overlap)))
        else:
            write_xosc(datum, generate_scenario_name(base,speed=str(round(float(speed)*3.6))))

def do_zip_compress(dirpath):
    # 修改自： https://blog.csdn.net/qq_39816613/article/details/125338232
    print("原始文件夹路径：" + dirpath)
    output_name = f"{dirpath}.zip"
    parent_name = os.path.dirname(dirpath)
    print("压缩文件夹目录：", parent_name)
    zip = zipfile.ZipFile(output_name, "w", zipfile.ZIP_DEFLATED)
    # 多层级压缩
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            if str(file).startswith("~$") or '.xosc' not in file:
                continue
            filepath = os.path.join(root, file)
            # print("压缩文件路径：" + filepath)
            writepath = os.path.relpath(filepath, dirpath)
            zip.write(filepath, writepath)
    print("压缩完成...\n")

# 检测指定文件夹是否含有INIT_NEW_FOLDER_NAME
def is_new(dirpath):
    global INIT_NEW_FOLDER_NAME
    if INIT_NEW_FOLDER_NAME in dirpath.split('/')[-1]:
        return True
    return False

def delete_intermediate_folder():
    if platform.system() == 'Linux':
                os.system(f'rm -rf {NEW_FOLDER_NAME}')                  # 删除原本的输出目录，仅保留压缩包 ------- 适用于UNIX
    elif platform.system() == 'Windows':
        win_path = '\\'.join(NEW_FOLDER_NAME.split('/'))        # 删除原本的输出目录，仅保留压缩包 ------- 适用于Windows
        os.system(f"rmdir /s/q {win_path}")

def main():
    global CONFIG
    CONFIG = JSON_Loader("./test")
    if CONFIG.config['auto_mode']:
        set_new_folder_suffix(CONFIG.config['suffix'])
        print(f"新生成的场景所在文件夹的后缀为：{INIT_NEW_FOLDER_NAME}")
        option = CONFIG.config['function']
        if option == "1":
            print("将启动批量修改功能")
        elif option == "2":
            print("将启动泛化功能")
        operate_path = CONFIG.config['root_path'] if option == '1' else "./"
        pass
    else:
        set_new_folder_suffix( input("请输入新生成的场景所在文件夹的后缀(默认为new):") )
        option = input("批量修改请按1, 泛化请按2: ")
        operate_path = input("请输入xosc所在的文件夹路径(根目录): ") if option == '1' else "./"
    print(f"将在 [{operate_path}] 路径下执行本程序...")

    if option == "1":
        if CONFIG.config['auto_mode']:
            batch_modifier = Batch_modifier(CONFIG.config)
        else:
            batch_modifier = Batch_modifier()

        for root, dirs, files in os.walk(operate_path):
            if is_new(root):                                # 如果目录是之前运行该脚本时生成的，则跳过该次循环
                continue
            set_new_folder_name(root)
            fnames = read_xosc(root)
            print("\n")
            if len(fnames) == 0:
                continue

            batch_modifier.batch_modify(fnames)
            do_zip_compress(NEW_FOLDER_NAME)
            delete_intermediate_folder()
            
    elif option == "2":
        fnames = read_xosc(strict=True)
        set_new_folder_name(addition=fnames[0].split('_')[0])
        generalize(fnames[0])
        do_zip_compress(NEW_FOLDER_NAME)
        delete_intermediate_folder()

if __name__ == "__main__":
    
    print("温馨提示: 使用该脚本前, 请将需要修改的场景解压到单独一个文件夹下(支持批量处理指定路径下的次级文件夹) \n如需修改主车模型, 请将对应的JSON文件放置在当前目录下:)\n如需修改对手车模型, 请将agents.json文件放置在当前目录。该文件可以在51simone的安装目录下/Module/VehicleDynamics/obstacle下找到:3")
    main()
    print("运行完毕┌(!￣◇￣)┘...")
    input("Press Enter to excit......")