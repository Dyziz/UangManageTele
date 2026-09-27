import io
from typing import Dict, List, Tuple
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def generate_rekap_chart(data: Dict[str, int], total_expense: int, title: str = "Pengeluaran Bulan Ini") -> io.BytesIO:
    """
    Renders a sleek dark-mode donut chart for Telegram sendPhoto.
    Returns BytesIO containing PNG image data.
    """
    if not data or total_expense <= 0:
        fig, ax = plt.subplots(figsize=(6.5, 5.5), facecolor='#1E1E2E')
        ax.set_facecolor('#1E1E2E')
        ax.pie([1], colors=['#313244'], wedgeprops=dict(width=0.42, edgecolor='#1E1E2E', linewidth=2.5))
        ax.text(0, 0, "Rp 0\n(Kosong)", ha='center', va='center', fontsize=14, fontweight='bold', color='#A6ADC8')
        ax.set_title(title, fontsize=13, fontweight='bold', color='#CDD6F4', pad=15)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        return buf

    # Modern color palette
    colors = [
        '#FF6B6B', '#4D96FF', '#6BCB77', '#FFD93D', 
        '#9B51E0', '#FF9F43', '#00D2D3', '#54A0FF'
    ]

    labels = list(data.keys())
    values = list(data.values())

    # Sort descending
    sorted_pairs = sorted(zip(values, labels), reverse=True)
    values = [p[0] for p in sorted_pairs]
    labels = [p[1] for p in sorted_pairs]

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(6.5, 5.5), facecolor='#1E1E2E')
    ax.set_facecolor('#1E1E2E')

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        pctdistance=0.76,
        startangle=140,
        colors=colors[:len(values)],
        wedgeprops=dict(width=0.42, edgecolor='#1E1E2E', linewidth=2.5),
        textprops=dict(color='#CDD6F4', fontsize=10, fontweight='medium')
    )

    for autotext in autotexts:
        autotext.set_color('#11111B')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(9.5)

    center_text = f"Total\nRp {total_expense:,.0f}".replace(',', '.')
    ax.text(0, 0, center_text, ha='center', va='center', fontsize=13, fontweight='bold', color='#FFFFFF')
    ax.set_title(title, fontsize=13, fontweight='bold', color='#CDD6F4', pad=15)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf

def generate_text_bars(data: Dict[str, int], total_expense: int) -> str:
    """
    Generates compact textual progress bars for Telegram text preview.
    Example:
    🍔 Makanan & Minuman [██████░░░░] 60.0% (Rp 60.000)
    """
    if not data or total_expense <= 0:
        return "Belum ada catatan pengeluaran."

    # Sort descending
    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    lines = []
    bar_width = 8

    category_emojis = {
        'Makanan & Minuman': '🍔',
        'Transportasi': '🛵',
        'Top Up / E-Wallet': '📱',
        'Belanja': '🛍️',
        'Tagihan': '💡',
        'Hiburan': '🎮',
        'Pendapatan': '💵',
        'Lain-lain': '📦'
    }

    for cat, val in sorted_items:
        percentage = (val / total_expense) * 100
        filled = int((val / total_expense) * bar_width)
        empty = bar_width - filled
        bar = "█" * filled + "░" * empty
        emoji = category_emojis.get(cat, '🔹')
        lines.append(f"{emoji} <b>{cat}</b>\n  <code>[{bar}]</code> {percentage:.1f}% (Rp {val:,.0f})".replace(',', '.'))

    return "\n".join(lines)
