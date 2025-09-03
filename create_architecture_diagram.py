import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 创建图形
fig, ax = plt.subplots(1, 1, figsize=(14, 8))
ax.set_xlim(0, 12)
ax.set_ylim(0, 8)
ax.axis('off')

# 定义颜色方案
colors = {
    'data_source': '#3498db',      # 蓝色
    'storage': '#e74c3c',          # 红色
    'analysis': '#2ecc71',         # 绿色
    'display': '#f39c12',          # 橙色
    'akshare': '#9b59b6',          # 紫色
    'arrow': '#34495e'             # 深灰色
}

# 模块定义
modules = [
    {
        'name': '数据获取\nData Acquisition', 
        'pos': (1, 5.5), 
        'size': (2.2, 1.5), 
        'color': colors['data_source'],
        'details': ['• 股票价格数据', '• 基本面数据', '• 实时数据更新']
    },
    {
        'name': '数据存储\nData Storage', 
        'pos': (4.5, 5.5), 
        'size': (2.2, 1.5), 
        'color': colors['storage'],
        'details': ['• SQLite数据库', '• 高效索引', '• 增量更新']
    },
    {
        'name': '回测分析\nBacktest Analysis', 
        'pos': (8, 5.5), 
        'size': (2.2, 1.5), 
        'color': colors['analysis'],
        'details': ['• 策略执行', '• 风险分析', '• 指标计算']
    },
    {
        'name': '结果展示\nResult Display', 
        'pos': (4.5, 2.5), 
        'size': (2.2, 1.5), 
        'color': colors['display'],
        'details': ['• 收益曲线', '• 统计报表', '• 交互图表']
    }
]

# 绘制模块
for module in modules:
    # 主模块框
    fancy_box = FancyBboxPatch(
        module['pos'], module['size'][0], module['size'][1],
        boxstyle="round,pad=0.1",
        facecolor=module['color'],
        edgecolor='white',
        linewidth=3,
        alpha=0.9
    )
    ax.add_patch(fancy_box)
    
    # 模块标题
    ax.text(module['pos'][0] + module['size'][0]/2, 
            module['pos'][1] + module['size'][1] - 0.3,
            module['name'], 
            ha='center', va='center', 
            fontsize=12, fontweight='bold', color='white')
    
    # 模块详细信息
    detail_text = '\n'.join(module['details'])
    ax.text(module['pos'][0] + module['size'][0]/2, 
            module['pos'][1] + 0.3,
            detail_text, 
            ha='center', va='center', 
            fontsize=9, color='white')

# AKShare特别标识
akshare_box = FancyBboxPatch(
    (0.5, 3.5), 3.2, 0.8,
    boxstyle="round,pad=0.1",
    facecolor=colors['akshare'],
    edgecolor='white',
    linewidth=2,
    alpha=0.9
)
ax.add_patch(akshare_box)

ax.text(2.1, 3.9, 'AKShare 数据源', ha='center', va='center', 
        fontsize=11, fontweight='bold', color='white')
ax.text(2.1, 3.6, 'github.com/akfamily/akshare', ha='center', va='center', 
        fontsize=9, color='white', style='italic')

# 绘制箭头
arrows = [
    # 数据获取 -> 数据存储
    {'start': (3.2, 6.25), 'end': (4.5, 6.25), 'label': '数据存储'},
    # 数据存储 -> 回测分析  
    {'start': (6.7, 6.25), 'end': (8, 6.25), 'label': '数据处理'},
    # 回测分析 -> 结果展示
    {'start': (9.1, 5.5), 'end': (5.6, 4.0), 'label': '结果输出'},
    # AKShare -> 数据获取
    {'start': (2.1, 4.3), 'end': (2.1, 5.5), 'label': ''}
]

for arrow in arrows:
    # 绘制箭头
    ax.annotate('', xy=arrow['end'], xytext=arrow['start'],
                arrowprops=dict(arrowstyle='->', lw=3, color=colors['arrow']))
    
    # 添加标签（如果有的话）
    if arrow['label']:
        mid_x = (arrow['start'][0] + arrow['end'][0]) / 2
        mid_y = (arrow['start'][1] + arrow['end'][1]) / 2 + 0.2
        ax.text(mid_x, mid_y, arrow['label'], ha='center', va='center',
                fontsize=8, color=colors['arrow'], fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))

# 添加流程说明
flow_steps = [
    "1. AKShare获取股票数据",
    "2. SQLite存储历史数据", 
    "3. 执行低价股策略回测",
    "4. 生成可视化报告"
]

for i, step in enumerate(flow_steps):
    ax.text(0.5, 1.5 - i*0.3, step, ha='left', va='center',
            fontsize=10, color='#2c3e50',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='#ecf0f1', alpha=0.8))

# 添加标题
ax.text(6, 7.5, '股票回测系统架构图', ha='center', va='center', 
        fontsize=18, fontweight='bold', color='#2c3e50')

# 添加副标题
ax.text(6, 7.1, 'Stock Backtesting System Architecture', ha='center', va='center', 
        fontsize=12, color='#7f8c8d', style='italic')

plt.tight_layout()
plt.savefig('/Users/dielangli/Desktop/Coding/股票回测/system_architecture.png', 
            dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
plt.show()

print("系统架构图已保存为: system_architecture.png")