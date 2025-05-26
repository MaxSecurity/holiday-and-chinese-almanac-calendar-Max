import os
import json
import re
from icalendar import Calendar, Event, vText, Timezone, TimezoneStandard
from datetime import datetime, timedelta
import logging

# 设置日志格式
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载干支数据
def load_ganzhi_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"未找到文件：{file_path}")
    except json.JSONDecodeError:
        logging.error(f"解析 JSON 文件出错：{file_path}")
    return {}

# 提取天干地支
def get_ganzhi_from_data(year, month, day, ganzhi_data):
    date_key = f"{year}-{month:02d}-{day:02d}"
    return ganzhi_data.get(date_key, "未知天干地支")

# 加载节庆数据
def load_festival_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['日期']: item['节庆'] for item in data.get('祭祀日程', [])}
    except FileNotFoundError:
        logging.error(f"未找到文件：{file_path}")
    except json.JSONDecodeError:
        logging.error(f"解析 JSON 文件出错：{file_path}")
    return {}

# 加载节气数据
def load_jieqi_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['节气']: item['节庆'] for item in data.get('祭祀日程', [])}
    except FileNotFoundError:
        logging.error(f"未找到文件：{file_path}")
    except json.JSONDecodeError:
        logging.error(f"解析 JSON 文件出错：{file_path}")
    return {}

# 清理描述字符串
def clean_description(text):
    text = text.replace("\\,", ",")
    text = re.sub(r',六九', '', text)
    return text.strip()

# 添加节气和神明信息
def add_jieqi_and_deity_info(festival_name, festival_details, jieqi_data, deity_data):
    jieqi_info = ""
    if festival_name or festival_details:
        for jieqi, jieqi_festival in jieqi_data.items():
            if jieqi in str(festival_name) or jieqi in str(festival_details):
                jieqi_info += f"\n🌱 **节气**: {jieqi} - {jieqi_festival}"

    deity_info = ""
    if festival_name or festival_details:
        for deity_date, deity_name in deity_data.items():
            if deity_date in str(festival_name) or deity_date in str(festival_details):
                deity_info += f"\n🕊️ **神明诞辰**: {deity_name} ({deity_date})"

    return festival_details + jieqi_info + deity_info

# 创建事件
def create_event(item, calendar, festival_data, jieqi_data, deity_data, ganzhi_data):
    try:
        timestamp = int(item['timestamp'])
        event_date = datetime.fromtimestamp(timestamp)
        dt = event_date.replace(hour=8, minute=30, second=0, microsecond=0)
        nongli = f"{item.get('lMonth', '')}月{item.get('lDate', '')}"

        ganzhi_info = get_ganzhi_from_data(event_date.year, event_date.month, event_date.day, ganzhi_data)

        festival_name = ','.join([f['name'] for f in item.get('festivalInfoList', [])]) if 'festivalInfoList' in item else item.get('festivalList', '')
        festival_name = clean_description(festival_name) or None

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
            for deity in festival_details.split('；'):
                description += f"  - {deity.strip()}\n"
        description += f"✅ **宜**: {item.get('suit', '')}\n"
        description += f"❌ **忌**: {item.get('avoid', '')}\n"

        event = Event()
        event.add('summary', f"★黄历★:{nongli}")
        event.add('dtstart', dt)
        event.add('dtend', dt)
        event.add('dtstamp', datetime.now())
        event.add('uid', f"{event_date.strftime('%Y%m%d')}_jr")
        event.add('created', datetime.now())
        event.add('description', vText(description))
        event.add('last-modified', datetime.now())
        event.add('sequence', 0)
        event.add('status', 'CONFIRMED')
        event.add('transp', 'TRANSPARENT')

        calendar.add_component(event)
        logging.debug(f"Added event: {event}")
    except Exception as e:
        logging.error(f"事件生成失败: {item}, 错误: {e}")

# 处理年度数据
def generate_ical_for_year(base_path, year, calendar, festival_data, jieqi_data, deity_data, ganzhi_data):
    year_path = os.path.join(base_path, str(year))
    if not os.path.exists(year_path):
        logging.warning(f"路径 {year_path} 不存在，跳过该年份。")
        return

    for file_name in os.listdir(year_path):
        if file_name.endswith('.json') and file_name != f"{year}.json":
            file_path = os.path.join(year_path, file_name)
            logging.info(f"正在处理文件: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    almanac = data['Result'][0]['DisplayData']['resultData']['tplData']['data']['almanac']
                    for item in almanac:
                        create_event(item, calendar, festival_data, jieqi_data, deity_data, ganzhi_data)
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"解析错误 {file_path}: {e}")

# 创建最终 iCal 文件
def create_final_ical(base_path, festival_data, jieqi_data, deity_data, ganzhi_data):
    cal = Calendar()
    cal.add('VERSION', '2.0')
    cal.add('PRODID', '-//My Calendar Product//mxm.dk//')
    cal.add('METHOD', 'PUBLISH')
    cal.add('X-WR-CALNAME', '节假日和黄历')
    cal.add('X-WR-TIMEZONE', 'Asia/Shanghai')
    cal.add('X-WR-CALDESC', f'中国及传统节庆与黄历日程，更新于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    timezone = Timezone()
    timezone.add('TZID', 'Asia/Shanghai')
    timezone.add('X-LIC-LOCATION', 'Asia/Shanghai')
    standard = TimezoneStandard()
    standard.add('TZOFFSETFROM', timedelta(hours=8))
    standard.add('TZOFFSETTO', timedelta(hours=8))
    standard.add('TZNAME', 'CST')
    standard.add('DTSTART', datetime(1970, 1, 1, 0, 0))
    timezone.add_component(standard)
    cal.add_component(timezone)

    for year in range(2025, 2051):
        generate_ical_for_year(base_path, year, cal, festival_data, jieqi_data, deity_data, ganzhi_data)

    output_path = os.path.join(base_path, f'holidays_calendar_2025-2050.ics')
    with open(output_path, 'wb') as f:
        f.write(cal.to_ical())
    logging.info(f"iCalendar 文件已生成: {output_path}")

# 主程序入口
def main():
    base_path = './openApiData/calendar_new'
    festival_data = load_festival_data('./shenxian.json')
    jieqi_data = load_jieqi_data('./jieqi.json')
    deity_data = load_festival_data('./deity.json')
    ganzhi_data = load_ganzhi_data('./ganzhi_data.json')
    create_final_ical(base_path, festival_data, jieqi_data, deity_data, ganzhi_data)

if __name__ == "__main__":
    main()
