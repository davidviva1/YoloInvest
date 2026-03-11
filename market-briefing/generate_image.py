#!/usr/bin/env python3
"""
Generate professional market briefing image (Bloomberg/McKinsey style)
"""
from PIL import Image, ImageDraw, ImageFont
import json
from datetime import datetime
import textwrap

# 专业配色方案（Bloomberg风格）
BG_COLOR = (255, 255, 255)  # 白色背景
HEADER_BG = (0, 51, 102)    # 深蓝色标题栏
SECTION_BG = (240, 244, 248)  # 浅灰色区块
TEXT_PRIMARY = (17, 24, 39)   # 深灰色主文本
TEXT_SECONDARY = (107, 114, 128)  # 中灰色副文本
GREEN = (16, 185, 129)        # 专业绿
RED = (239, 68, 68)           # 专业红
ACCENT = (59, 130, 246)       # 蓝色强调
BORDER = (229, 231, 235)      # 边框灰

WIDTH = 1400
PADDING = 60

def load_data():
    """加载所有数据"""
    with open("/tmp/market_data.json") as f:
        market = json.load(f)
    
    try:
        with open("/tmp/news_analysis.txt") as f:
            analysis = f.read()
    except:
        analysis = "暂无分析"
    
    try:
        with open("/tmp/earnings_calendar.json") as f:
            earnings = json.load(f)
    except:
        earnings = []
    
    try:
        with open("/tmp/economic_data.json") as f:
            economic = json.load(f)
    except:
        economic = {"calendar": []}
    
    return market, analysis, earnings, economic

def wrap_text(text, font, max_width, draw):
    """智能换行（支持中文）"""
    lines = []
    paragraphs = text.split('\n')
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            lines.append("")
            continue
            
        words = paragraph
        current_line = ""
        
        for char in words:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        
        if current_line:
            lines.append(current_line)
    
    return lines

def draw_section_header(draw, y, text, font, icon=""):
    """绘制区块标题"""
    # 背景条
    draw.rectangle([0, y, WIDTH, y+60], fill=SECTION_BG)
    # 左侧强调条
    draw.rectangle([0, y, 8, y+60], fill=ACCENT)
    # 标题文字
    full_text = f"{icon} {text}" if icon else text
    draw.text((PADDING, y+15), full_text, fill=TEXT_PRIMARY, font=font)
    return y + 70

def draw_card(draw, x, y, width, height, content_func):
    """绘制卡片"""
    # 卡片背景
    draw.rectangle([x, y, x+width, y+height], fill=(255, 255, 255), outline=BORDER, width=2)
    # 内容
    content_func(draw, x, y, width, height)
    return y + height + 20

def create_professional_briefing(market_data, analysis, earnings, economic):
    """生成专业简报图片"""
    
    # 预估高度
    height = 3500
    img = Image.new('RGB', (WIDTH, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # 加载中文字体
    font_path = "/home/ec2-user/.openclaw/workspace/market-briefing/fonts/NotoSansCJK-Regular.ttc"
    try:
        title_font = ImageFont.truetype(font_path, 56)
        header_font = ImageFont.truetype(font_path, 36)
        subheader_font = ImageFont.truetype(font_path, 28)
        body_font = ImageFont.truetype(font_path, 24)
        small_font = ImageFont.truetype(font_path, 20)
    except:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        subheader_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    y = 0
    
    # ===== 顶部标题栏 =====
    draw.rectangle([0, 0, WIDTH, 120], fill=HEADER_BG)
    today = datetime.now().strftime("%Y年%m月%d日")
    draw.text((PADDING, 30), "市场简报", fill=(255, 255, 255), font=title_font)
    draw.text((PADDING, 80), today, fill=(200, 200, 200), font=body_font)
    
    # 右上角时间戳
    timestamp = datetime.now().strftime("%H:%M UTC")
    draw.text((WIDTH - PADDING - 200, 80), f"更新时间: {timestamp}", fill=(200, 200, 200), font=small_font)
    
    y = 140
    
    # ===== 新闻影响分析 =====
    y = draw_section_header(draw, y, "新闻影响分析", header_font, "📰")
    
    # 分析文本（智能换行）
    analysis_lines = wrap_text(analysis[:1200], body_font, WIDTH - 2*PADDING, draw)
    
    for line in analysis_lines:
        if line.strip():
            draw.text((PADDING, y), line, fill=TEXT_PRIMARY, font=body_font)
        y += 32
    
    y += 30
    
    # ===== 市场概览（三栏布局）=====
    y = draw_section_header(draw, y, "市场概览", header_font, "📊")
    
    card_width = (WIDTH - 2*PADDING - 40) // 3
    card_x = PADDING
    
    # 加密货币卡片
    def draw_crypto(draw, x, y, w, h):
        cy = y + 20
        draw.text((x+20, cy), "💰 加密货币", fill=TEXT_PRIMARY, font=subheader_font)
        cy += 50
        for symbol, data in market_data["crypto"].items():
            color = GREEN if data["change"] >= 0 else RED
            draw.text((x+20, cy), symbol, fill=TEXT_SECONDARY, font=small_font)
            draw.text((x+20, cy+25), f"${data['price']:.2f}", fill=TEXT_PRIMARY, font=body_font)
            draw.text((x+20, cy+55), f"{data['changePercent']:+.2f}%", fill=color, font=body_font)
            cy += 95
    
    draw_card(draw, card_x, y, card_width, 350, draw_crypto)
    
    # 大宗商品卡片
    def draw_commodities(draw, x, y, w, h):
        cy = y + 20
        draw.text((x+20, cy), "🛢️ 大宗商品", fill=TEXT_PRIMARY, font=subheader_font)
        cy += 50
        count = 0
        for name, data in market_data["commodities"].items():
            if count >= 3:  # 只显示前3个
                break
            color = GREEN if data["change"] >= 0 else RED
            draw.text((x+20, cy), name, fill=TEXT_SECONDARY, font=small_font)
            draw.text((x+20, cy+25), f"${data['price']:.2f}", fill=TEXT_PRIMARY, font=body_font)
            draw.text((x+20, cy+55), f"{data['changePercent']:+.2f}%", fill=color, font=body_font)
            cy += 95
            count += 1
    
    draw_card(draw, card_x + card_width + 20, y, card_width, 350, draw_commodities)
    
    # 涨跌幅榜卡片
    def draw_movers(draw, x, y, w, h):
        cy = y + 20
        draw.text((x+20, cy), "📈 涨跌幅", fill=TEXT_PRIMARY, font=subheader_font)
        cy += 50
        
        # 收集所有股票
        all_stocks = []
        for category, stocks in market_data["stocks"].items():
            for symbol, data in stocks.items():
                all_stocks.append((symbol, data))
        all_stocks.sort(key=lambda x: x[1]["changePercent"], reverse=True)
        
        # 涨幅前2
        for symbol, data in all_stocks[:2]:
            draw.text((x+20, cy), f"↑ {symbol}", fill=GREEN, font=small_font)
            draw.text((x+20, cy+25), f"+{data['changePercent']:.2f}%", fill=GREEN, font=body_font)
            cy += 60
        
        cy += 10
        
        # 跌幅前2
        for symbol, data in all_stocks[-2:]:
            draw.text((x+20, cy), f"↓ {symbol}", fill=RED, font=small_font)
            draw.text((x+20, cy+25), f"{data['changePercent']:.2f}%", fill=RED, font=body_font)
            cy += 60
    
    draw_card(draw, card_x + 2*(card_width + 20), y, card_width, 350, draw_movers)
    
    y += 380
    
    # ===== 板块表现 =====
    y = draw_section_header(draw, y, "板块表现", header_font, "📊")
    
    for category, stocks in market_data["stocks"].items():
        # 板块标题
        draw.text((PADDING, y), category, fill=TEXT_PRIMARY, font=subheader_font)
        y += 45
        
        # 股票列表（表格形式）
        for symbol, data in list(stocks.items())[:6]:  # 每个板块最多6只
            color = GREEN if data["change"] >= 0 else RED
            
            # 股票代码
            draw.text((PADDING + 20, y), symbol, fill=TEXT_PRIMARY, font=body_font)
            # 价格
            draw.text((PADDING + 200, y), f"${data['price']:.2f}", fill=TEXT_SECONDARY, font=body_font)
            # 涨跌幅
            draw.text((PADDING + 400, y), f"{data['changePercent']:+.2f}%", fill=color, font=body_font)
            # 成交量
            if data.get('volume'):
                vol_str = f"{data['volume']/1e6:.1f}M"
                draw.text((PADDING + 600, y), vol_str, fill=TEXT_SECONDARY, font=small_font)
            
            y += 40
        
        y += 20
    
    # ===== 本周日历 =====
    if earnings or economic.get("calendar"):
        y = draw_section_header(draw, y, "本周日历", header_font, "📅")
        
        # 经济数据
        if economic.get("calendar"):
            draw.text((PADDING, y), "重要经济数据", fill=TEXT_PRIMARY, font=subheader_font)
            y += 45
            for event in economic["calendar"][:5]:
                draw.text((PADDING + 20, y), f"• {event['date']}: {event['event']}", fill=TEXT_SECONDARY, font=body_font)
                y += 35
            y += 20
        
        # 财报
        if earnings:
            draw.text((PADDING, y), "财报发布", fill=TEXT_PRIMARY, font=subheader_font)
            y += 45
            for e in earnings[:8]:
                draw.text((PADDING + 20, y), f"• {e['date']}: {e['symbol']}", fill=TEXT_SECONDARY, font=body_font)
                y += 35
    
    y += 60
    
    # ===== 底部信息栏 =====
    draw.rectangle([0, y, WIDTH, y+60], fill=SECTION_BG)
    draw.text((PADDING, y+18), "数据来源: Yahoo Finance | 分析: Claude AI", fill=TEXT_SECONDARY, font=small_font)
    
    y += 60
    
    # 裁剪到实际高度
    img = img.crop((0, 0, WIDTH, y))
    
    return img

if __name__ == "__main__":
    print("Loading data...")
    market, analysis, earnings, economic = load_data()
    
    print("Generating professional briefing image...")
    img = create_professional_briefing(market, analysis, earnings, economic)
    
    output_path = "/tmp/market_briefing.png"
    img.save(output_path, quality=95)
    
    print(f"Image saved to {output_path}")
    print(f"Size: {img.size}")
