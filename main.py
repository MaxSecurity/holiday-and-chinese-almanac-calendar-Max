import os
import json
import re  # 确保导入了正则表达式模块
from icalendar import Calendar, Event, vText, vDatetime, vDate, Timezone, TimezoneStandard
from datetime import datetime, timedelta
import logging
import pytz  # 用于处理时区

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# 读取节庆数据 (shenxian.json)
def load_festival_data(file_path):
    """加载本地节庆数据文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['日期']: item['节庆'] for item in data.get('祭祀日程', [])}
    except FileNotFoundError:
        logging.error(f"未找到文件：{file_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"解析 JSON 文件出错：{file_path}")
        return {}


# 读取节气数据 (jieqi.json)
def load_jieqi_data(file_path):
    """加载本地节气数据文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['节气']: item['节庆'] for item in data.get('祭祀日程', [])}
    except FileNotFoundError:
        logging.error(f"未找到文件：{file_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"解析 JSON 文件出错：{file_path}")
        return {}


# 清理描述中的无效数据或特殊字符
def clean_description(text):
    """清理节庆名称或描述中的无效字符"""
    text = text.replace("\\,", ",")  # 移除不必要的转义字符
    text = re.sub(r',六九', '', text)  # 删除所有 "六九" 字符
    return text.strip()


# 将节气数据和神明诞辰信息分别添加到节庆描述中
def add_jieqi_and_deity_info(festival_name, festival_details, jieqi_data, deity_data):
    """将节气数据和神明诞辰信息分别添加到节庆描述中"""
    # 节气信息
    jieqi_info = ""
    if festival_name and festival_details:  # 确保值不为None
        for jieqi, jieqi_festival in jieqi_data.items():
            if isinstance(festival_name, str) and jieqi in festival_name or isinstance(festival_details,
                                                                                       str) and jieqi in festival_details:
                jieqi_info += f"\n🌱 **节气**: {jieqi} - {jieqi_festival}"

    # 神明诞辰信息
    deity_info = ""
    if festival_name and festival_details:  # 确保值不为None
        for deity_date, deity_name in deity_data.items():
            if isinstance(festival_name, str) and deity_date in festival_name or isinstance(festival_details,
                                                                                            str) and deity_date in festival_details:
                deity_info += f"\n🕊️ **神明诞辰**: {deity_name} ({deity_date})"

    # 合并节气信息与神明诞辰信息
    festival_details += jieqi_info + deity_info
    return festival_details


# 创建事件
def create_event(item, calendar, festival_data, jieqi_data, deity_data):
    try:
        timestamp = int(item['timestamp'])
        event_date = datetime.fromtimestamp(timestamp)
        nongli = f"{item.get('lMonth', '')}月{item.get('lDate', '')}"

        # 获取节庆的名称和描述
        festival_name = ','.join(
            [f['name'] for f in item.get('festivalInfoList', [])]) if 'festivalInfoList' in item else item.get(
            'festivalList', '')

        # 清理节庆名称
        festival_name = clean_description(festival_name)

        # 如果节庆名称为空，跳过
        if not festival_name:
            festival_name = None

        festival_details = festival_data.get(nongli, '')  # 从节庆数据中获取详细描述
        festival_details = clean_description(festival_details)

        # 添加节气数据和神明诞辰信息
        festival_details = add_jieqi_and_deity_info(festival_name, festival_details, jieqi_data, deity_data)

        # 格式化描述内容，让其更整洁
        description = ""
        if festival_name:
            description += f"🎉 **节庆**: {festival_name}\n"  # 只有在节庆名称存在时才添加此行
        description += f"📅 **农历**: {nongli}\n"  # 农历日期

        # 只有在 festival_details 有数据时才添加神明描述
        if festival_details:
            description += f"🌟 **神仙**:\n"  # 神明部分标题
            # 优化神明的展示格式
            deity_list = festival_details.split('；')  # 假设每个神明名称之间用中文分号分隔
            for deity in deity_list:
                description += f"  - {deity.strip()}\n"  # 每个神明用缩进和符号列表展示

        description += f"✅ **宜**: {item['suit']}\n"  # 宜做的事项
        description += f"❌ **忌**: {item['avoid']}\n"  # 忌做的事项

        # 创建事件
        event = Event()
        event.add('summary', f"★黄历★:{nongli}")  # 只保留 ★黄历★:日期
        # 设置事件的开始和结束时间
        event.add('dtstart', vDatetime(event_date.replace(hour=8, minute=30, second=0, microsecond=0)))  # 精确到当天8:30
        event.add('dtend', vDatetime(event_date.replace(hour=8, minute=30, second=0, microsecond=0)))  # 结束时间为当天8:30
        event.add('dtstamp', vDatetime(datetime.now()))
        event.add('uid', f"{event_date.strftime('%Y%m%d')}_jr")
        event.add('created', vDatetime(datetime.now()))
        event.add('description', vText(description))
        event.add('last-modified', vDatetime(datetime.now()))
        event.add('sequence', 0)
        event.add('status', 'CONFIRMED')
        event.add('transp', 'TRANSPARENT')

        # 不添加任何提醒

        # 将事件添加到日历
        calendar.add_component(event)
        logging.debug(f"Added event: {event}")
    except Exception as e:
        logging.error(f"Error processing item: {item}, error: {e}")


# 生成某一年份的iCalendar
def generate_ical_for_year(base_path, year, final_calendar, festival_data, jieqi_data, deity_data):
    year_path = os.path.join(base_path, str(year))
    if not os.path.exists(year_path):
        logging.warning(f"路径 {year_path} 不存在，跳过该年份。")
        return

    # 遍历年份路径下的文件，处理每个json文件
    for file_name in os.listdir(year_path):
        if file_name.endswith('.json') and file_name != f"{year}.json":  # 排除总年份文件
            file_path = os.path.join(year_path, file_name)
            logging.info(f"正在处理文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    # 遍历黄历数据中的每个项，创建事件
                    for item in data['Result'][0]['DisplayData']['resultData']['tplData']['data']['almanac']:
                        create_event(item, final_calendar, festival_data, jieqi_data, deity_data)
                except json.JSONDecodeError:
                    logging.error(f"Error decoding JSON from file: {file_path}")
                except KeyError:
                    logging.error(f"Key error in file: {file_path}")


# 创建最终的iCalendar文件
def create_final_ical(base_path, festival_data, jieqi_data, deity_data):
    final_calendar = Calendar()
    final_calendar.add('VERSION', '2.0')
    final_calendar.add('PRODID', '-//My Calendar Product//mxm.dk//')
    final_calendar.add('METHOD', 'PUBLISH')
    final_calendar.add('X-WR-CALNAME', '节假日和黄历')
    final_calendar.add('X-WR-TIMEZONE', 'Asia/Shanghai')
    final_calendar.add('X-WR-CALDESC',
                       f'中国以及国际节假日，备注有黄历，更新日期:{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    # 设置时区信息
    timezone = Timezone()
    timezone.add('TZID', 'Asia/Shanghai')
    timezone.add('X-LIC-LOCATION', 'Asia/Shanghai')
    standard = TimezoneStandard()
    standard.add('TZOFFSETFROM', timedelta(hours=8))
    standard.add('TZOFFSETTO', timedelta(hours=8))
    standard.add('TZNAME', 'CST')
    standard.add('DTSTART', datetime(1970, 1, 1, 0, 0, 0))
    timezone.add_component(standard)
    final_calendar.add_component(timezone)

    years = list(range(2022, 2031))
    for year in years:
        generate_ical_for_year(base_path, year, final_calendar, festival_data, jieqi_data, deity_data)

    output_file = os.path.join(base_path, f'holidays_calendar_{years[0]}-{years[-1]}.ics')  # 动态生成文件名
    with open(output_file, 'wb') as f:
        f.write(final_calendar.to_ical())
    logging.info(f"最终的iCalendar文件已成功生成：{output_file}")


def main():
    base_path = './openApiData/calendar_new'
    festival_data = load_festival_data('./shenxian.json')  # 加载节庆数据
    jieqi_data = load_jieqi_data('./jieqi.json')  # 加载节气数据
    deity_data = load_festival_data('./deity.json')  # 加载神明数据（假设有该数据）
    create_final_ical(base_path, festival_data, jieqi_data, deity_data)


if __name__ == "__main__":
    main()
