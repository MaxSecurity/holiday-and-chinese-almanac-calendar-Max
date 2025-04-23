import os
import json
import re
from icalendar import Calendar, Event, vText, vDatetime, Timezone, TimezoneStandard
from datetime import datetime, timedelta
import logging

# 设置日志记录格式和级别
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载干支数据
def load_ganzhi_data(file_path):
    """加载本地干支数据文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)  # 加载 JSON 数据
    except FileNotFoundError:
        logging.error(f"未找到文件：{file_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"解析 JSON 文件出错：{file_path}")
        return {}

# 从本地数据中获取干支信息
def get_ganzhi_from_data(ganzhi_data, year, month, day):
    """从本地干支数据中提取指定日期的干支信息"""
    date_key = f"{year}-{month:02d}-{day:02d}"  # 格式化日期为 YYYY-MM-DD
    return ganzhi_data.get(date_key, "未知天干地支")

# **函数功能：加载节庆数据**
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

# **函数功能：加载节气数据**
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

# **函数功能：清理描述中的无效数据或特殊字符**
def clean_description(text):
    """清理节庆名称或描述中的无效字符"""
    text = text.replace("\\,", ",")  # 移除不必要的转义字符
    text = re.sub(r',六九', '', text)  # 删除所有 "六九" 字符
    return text.strip()  # 去除首尾空格

# **函数功能：将节气和神明诞辰信息添加到节庆描述中**
def add_jieqi_and_deity_info(festival_name, festival_details, jieqi_data, deity_data):
    """将节气数据和神明诞辰信息分别添加到节庆描述中"""
    jieqi_info = ""
    if festival_name and festival_details:
        for jieqi, jieqi_festival in jieqi_data.items():
            if isinstance(festival_name, str) and jieqi in festival_name or isinstance(festival_details, str) and jieqi in festival_details:
                jieqi_info += f"\n🌱 **节气**: {jieqi} - {jieqi_festival}"

    deity_info = ""
    if festival_name and festival_details:
        for deity_date, deity_name in deity_data.items():
            if isinstance(festival_name, str) and deity_date in festival_name or isinstance(festival_details, str) and deity_date in festival_details:
                deity_info += f"\n🕊️ **神明诞辰**: {deity_name} ({deity_date})"

    festival_details += jieqi_info + deity_info
    return festival_details

# **函数功能：创建日历事件**
def create_event(item, calendar, festival_data, jieqi_data, deity_data, ganzhi_data):
    try:
        timestamp = int(item['timestamp'])
        event_date = datetime.fromtimestamp(timestamp)
        nongli = f"{item.get('lMonth', '')}月{item.get('lDate', '')}"

        # 获取干支信息
        ganzhi_info = get_ganzhi_from_data(ganzhi_data, event_date.year, event_date.month, event_date.day)

        festival_name = ','.join([f['name'] for f in item.get('festivalInfoList', [])]) if 'festivalInfoList' in item else item.get('festivalList', '')
        festival_name = clean_description(festival_name)

        if not festival_name:
            festival_name = None

        festival_details = festival_data.get(nongli, '')
        festival_details = clean_description(festival_details)
        festival_details = add_jieqi_and_deity_info(festival_name, festival_details, jieqi_data, deity_data)

        description = ""
        if festival_name:
            description += f"🎉 **节庆**: {festival_name}\n"
        description += f"📅 **农历**: {nongli}\n"
        description += f"🌀 **干支**: {ganzhi_info}\n"
        if festival_details:
            description += f"🌟 **神仙**:\n"
            deity_list = festival_details.split('；')
            for deity in deity_list:
                description += f"  - {deity.strip()}\n"
        description += f"✅ **宜**: {item['suit']}\n"
        description += f"❌ **忌**: {item['avoid']}\n"

        event = Event()
        event.add('summary', f"★黄历★:{nongli}")
        event.add('dtstart', vDatetime(event_date.replace(hour=8, minute=30, second=0, microsecond=0)))
        event.add('dtend', vDatetime(event_date.replace(hour=8, minute=30, second=0, microsecond=0)))
        event.add('dtstamp', vDatetime(datetime.now()))
        event.add('uid', f"{event_date.strftime('%Y%m%d')}_jr")
        event.add('created', vDatetime(datetime.now()))
        event.add('description', vText(description))
        event.add('last-modified', vDatetime(datetime.now()))
        event.add('sequence', 0)
        event.add('status', 'CONFIRMED')
        event.add('transp', 'TRANSPARENT')

        calendar.add_component(event)
        logging.debug(f"Added event: {event}")
    except Exception as e:
        logging.error(f"Error processing item: {item}, error: {e}")

# **函数功能：生成某年份的日历**
def generate_ical_for_year(base_path, year, final_calendar, festival_data, jieqi_data, deity_data, ganzhi_data):
    year_path = os.path.join(base_path, str(year))
    if not os.path.exists(year_path):
        logging.warning(f"路径 {year_path} 不存在，跳过该年份。")
        return

    for file_name in os.listdir(year_path):
        if file_name.endswith('.json') and file_name != f"{year}.json":
            file_path = os.path.join(year_path, file_name)
            logging.info(f"正在处理文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    for item in data['Result'][0]['DisplayData']['resultData']['tplData']['data']['almanac']:
                        create_event(item, final_calendar, festival_data, jieqi_data, deity_data, ganzhi_data)
                except json.JSONDecodeError:
                    logging.error(f"Error decoding JSON from file: {file_path}")
                except KeyError:
                    logging.error(f"Key error in file: {file_path}")

# **函数功能：创建最终的 iCalendar 文件**
def create_final_ical(base_path, festival_data, jieqi_data, deity_data, ganzhi_data):
    final_calendar = Calendar()
    final_calendar.add('VERSION', '2.0')
    final_calendar.add('PRODID', '-//My Calendar Product//mxm.dk//')
    final_calendar.add('METHOD', 'PUBLISH')
    final_calendar.add('X-WR-CALNAME', '节假日和黄历')
    final_calendar.add('X-WR-TIMEZONE', 'Asia/Shanghai')
    final_calendar.add('X-WR-CALDESC', f'中国以及国际节假日，备注有黄历，更新日期:{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

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

    years = list(range(2025, 2051))
    for year in years:
        generate_ical_for_year(base_path, year, final_calendar, festival_data, jieqi_data, deity_data, ganzhi_data)

    output_file = os.path.join(base_path, f'holidays_calendar_{years[0]}-{years[-1]}.ics')
    with open(output_file, 'wb') as f:
        f.write(final_calendar.to_ical())
    logging.info(f"最终的iCalendar文件已成功生成：{output_file}")

# **主函数入口**
def main():
    base_path = './openApiData/calendar_new'
    festival_data = load_festival_data('./shenxian.json')
    jieqi_data = load_jieqi_data('./jieqi.json')
    deity_data = load_festival_data('./deity.json')
    ganzhi_data = load_ganzhi_data('./ganzhi_data.json')
    create_final_ical(base_path, festival_data, jieqi_data, deity_data, ganzhi_data)

if __name__ == "__main__":
    main()