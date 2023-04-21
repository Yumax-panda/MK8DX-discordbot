from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from discord import File
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np


BOLD = ImageFont.truetype('fonts/NotoSansCJKjp-Bold.otf', size=80)
THIN = ImageFont.truetype('fonts/NotoSansCJKjp-Thin.otf', size=50)
FIRST = Image.open('images/first.png')
SECOND = Image.open('images/second.png')


def make(
    tags: list[str],
    score_history: list[list[int]],
    track_name: Optional[str] = None
) -> File:
    scores = np.array(score_history).sum(axis=0)
    diff_history = np.array([s[0]-s[1] for s in score_history]).cumsum()[-13:]
    min_diff = diff_history.min()
    max_diff = diff_history.max()

    if min_diff < 0 and max_diff > 0 and max(max_diff, -min_diff) // min(max_diff, -min_diff) < 3:
        y = [min_diff, 0, max_diff]
    else:
        y = [min_diff, (min_diff+max_diff)//2, max_diff]

    fig = plt.figure(figsize=(12.8, 3))
    fig.subplots_adjust(0.125, 0.1, 0.9, 0.85)
    ax = fig.add_subplot(111, xmargin=0, xticks=[], yticks=y)
    ax.tick_params(labelsize = 20)
    ax.grid(axis='y', color='#fffafa')
    ax.axhspan(min_diff, max_diff, color='grey', alpha=0.3)
    if min_diff <= 0 and max_diff >= 0:
        ax.plot([0]*len(diff_history), color='#fffafa')
    ax.plot(diff_history, color='#6495ed', linewidth=4)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', colors='#fffafa')
    buffer = BytesIO()
    fig.savefig(buffer, format='png', transparent=True)
    ax.cla()
    fig.clf()
    plt.clf()
    plt.close()
    buffer.seek(0)
    graph_img = Image.open(buffer)

    width, height = graph_img.size
    back_width = width
    back_height = height + 420

    if track_name is None:
        back_img = Image.new(graph_img.mode, (back_width, back_height), '#2c3e50')
    else:
        back_img = Image.open(f'images/{track_name}.png').copy().resize((back_width, back_height))

    back_img.paste(graph_img, (0, 420), graph_img)
    back_img.paste(FIRST, (10,165), FIRST)
    draw = ImageDraw.Draw(back_img)
    draw.line([(0, 0), (back_width, 0)], fill = '#afeeee', width = 40)
    draw.line([(0, back_height), (back_width, back_height)], fill = '#afeeee', width = 40)

    if scores[0] != scores[1]:
        back_img.paste(SECOND, (10,310), SECOND)
    else:
        back_img.paste(FIRST, (10, 310), FIRST)

    first_index = int(scores[0] < scores[1])
    second_index = int(int(scores[0] >= scores[1]))

    draw.text((130, 155), tags[first_index], fill='#F8F8FF', font=BOLD)
    draw.text((back_width-300, 155), str(scores[first_index]), fill='#F8F8FF', font=BOLD)
    draw.text((130, 300), tags[second_index], fill='#F8F8FF', font=BOLD)
    draw.text((back_width-300, 300), str(scores[second_index]), fill='#F8F8FF', font=BOLD)
    draw.text((back_img.width-260, 250), '({:+})'.format(abs(scores[0]-scores[1])), fill='#F8F8FF', font=THIN)
    b = BytesIO()
    back_img.save(b, 'png')
    b.seek(0)
    file = File(fp=b, filename='result.png', description=' '.join(tags))
    buffer.close()
    b.close()
    return file