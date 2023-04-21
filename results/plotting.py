import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from io import BytesIO


def result_graph(df: pd.DataFrame) -> BytesIO:
    xs = np.arange(len(df))
    lines = plt.plot(
        np.sign(df['score']-df['enemyScore']).cumsum(),
        label='Wins - Loses'
    )
    plt.setp(lines, color='green', linewidth=1.0)
    _, _, ymin, ymax = plt.axis()
    plt.grid(visible=True, which='both', axis='both', color='gray', linestyle=':')
    plt.legend(
        bbox_to_anchor=(0, 1),
        loc='upper left',
        borderaxespad=0.5
    )
    plt.fill_between(xs, ymin, 0, facecolor = '#87ceeb', alpha=0.3)
    plt.fill_between(xs, 0, ymax, facecolor = '#ffa07a', alpha=0.3)
    plt.title('Win&Lose History')
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    plt.clf()
    plt.close()
    return buffer