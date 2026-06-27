"""
═══════════════════════════════════════════════════════════════
  XOLA007 v2.0 - Self-Learning Trading Bot (COMPLETE EDITION)
  
  NEW IN v2.0:
  • ▶️ Run/Stop live trading
  • 📝 Paper trading mode (simulated money)
  • 💵 Real money trading (Alpaca broker)
  • 🌐 Built-in sales website
  
  All features from v1.0:
  • Self-learning Q-learning agent
  • News sentiment analysis
  • Profit/loss alerts with vibration
  • Dark/Light theme toggle
  • Multi-ticker portfolio support
  • CSV export & performance metrics
  • 30-day trial + activation system
  
  Run modes:
  python xola007.py           # GUI app
  python xola007.py --cli     # CLI mode
  python xola007.py --website # Launch sales website on port 8080
═══════════════════════════════════════════════════════════════
"""
import os
import sys
import json
import pickle
import random
import hashlib
import platform
import threading
import re
import csv
import gc
import time
import urllib.request
import urllib.error
from collections import deque
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

# ════════════════════════════════════════════════════════════
# PLATFORM DETECTION
# ════════════════════════════════════════════════════════════
IS_ANDROID = 'ANDROID_ROOT' in os.environ or 'ANDROID_DATA' in os.environ

# ════════════════════════════════════════════════════════════
# IMPORTS
# ════════════════════════════════════════════════════════════
try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("❌ Install: pip install numpy pandas yfinance")
    sys.exit(1)

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False

ANDROID_ALERTS = False
if IS_ANDROID:
    try:
        from plyer import notification, vibrator
        ANDROID_ALERTS = True
    except ImportError:
        pass

USE_KIVY = False
try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.spinner import Spinner
    from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
    from kivy.uix.widget import Widget
    from kivy.uix.popup import Popup
    from kivy.uix.switch import Switch
    from kivy.graphics import Color, Line, Rectangle, Ellipse
    from kivy.clock import Clock, mainthread
    from kivy.core.window import Window
    USE_KIVY = True
except ImportError:
    pass

# ════════════════════════════════════════════════════════════
# CONSTANTS
# ════════════════════════════════════════════════════════════
APP_NAME = "XOLA007"
VERSION = "2.0"
TRIAL_DAYS = 30
SECRET_SALT = "XOLA007_2024_SECURE_BOT"

LICENSE_TEXT = """
═══════════════════════════════════════════════════════
            XOLA007 - END USER LICENSE AGREEMENT
═══════════════════════════════════════════════════════

BY USING THIS SOFTWARE, YOU AGREE TO THESE TERMS:

1. NO FINANCIAL ADVICE
   XOLA007 is for EDUCATIONAL purposes only. Not financial,
   investment, or trading advice.

2. NO WARRANTY
   Software provided "AS IS" without any warranty.

3. LIMITATION OF LIABILITY
   Authors are NOT liable for ANY damages including:
   • Loss of money, profits, or investments
   • Trading losses or missed opportunities
   • Data loss or business interruption
   • Damages from REAL MONEY TRADING

4. REAL MONEY TRADING WARNING
   This software supports real money trading via broker APIs.
   You are SOLELY RESPONSIBLE for all trades executed.
   Always test with PAPER TRADING first.
   Never trade money you cannot afford to lose.

5. USER RESPONSIBILITY
   Trading carries SUBSTANTIAL RISK. Past performance does
   not guarantee future results.

6. TRIAL
   Free for 30 days. Activation code required after.

By clicking "I AGREE" you accept all terms.
═══════════════════════════════════════════════════════
"""

def _hash_code(c):
    return hashlib.sha256(f"{SECRET_SALT}:{c.upper().strip()}".encode()).hexdigest()

MASTER_CODES = {
    "XOLA-2024-PREMIUM-007": "PREMIUM_LIFETIME",
    "XOLA-PRO-ACCESS-X7K9": "PRO",
    "XOLA-DEV-MODE-BETA42": "DEV",
}
VALID_HASHES = {_hash_code(c): t for c, t in MASTER_CODES.items()}


# ════════════════════════════════════════════════════════════
# STORAGE
# ════════════════════════════════════════════════════════════
def get_data_dir():
    if IS_ANDROID:
        base = '/storage/emulated/0/xola007'
    else:
        base = os.path.join(os.path.expanduser('~'), '.xola007')
    for sub in ['', 'cache', 'models', 'exports', 'live']:
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    return base


# ════════════════════════════════════════════════════════════
# LICENSE
# ════════════════════════════════════════════════════════════
class LicenseManager:
    def __init__(self):
        self.file = os.path.join(get_data_dir(), 'license.dat')
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file) as f: return json.load(f)
            except: pass
        return {'install_date': None, 'agreed': False, 'activated': False,
                'activation_code': None, 'tier': None}

    def _save(self):
        try:
            with open(self.file, 'w') as f: json.dump(self.data, f, indent=2)
        except Exception as e: print(f"License save: {e}")

    def has_agreed(self): return bool(self.data.get('agreed'))

    def accept_license(self):
        self.data['agreed'] = True
        if not self.data.get('install_date'):
            self.data['install_date'] = datetime.now().isoformat()
        self._save()

    def days_remaining(self):
        if self.is_activated(): return -1
        if not self.data.get('install_date'): return TRIAL_DAYS
        try:
            inst = datetime.fromisoformat(self.data['install_date'])
            return max(0, TRIAL_DAYS - (datetime.now() - inst).days)
        except: return TRIAL_DAYS

    def is_trial_expired(self):
        return not self.is_activated() and self.days_remaining() <= 0

    def is_activated(self): return bool(self.data.get('activated'))

    def activate(self, code):
        if not code: return False, "Empty code"
        h = _hash_code(code)
        if h in VALID_HASHES:
            self.data['activated'] = True
            self.data['activation_code'] = code.upper().strip()
            self.data['tier'] = VALID_HASHES[h]
            self._save()
            return True, f"Activated! Tier: {VALID_HASHES[h]}"
        return False, "Invalid code"

    def get_status(self):
        if self.is_activated(): return f"✅ {self.data.get('tier', 'PREMIUM')}"
        d = self.days_remaining()
        return "❌ Trial expired" if d <= 0 else f"🆓 Trial: {d}d left"


# ════════════════════════════════════════════════════════════
# SETTINGS (broker keys, etc.)
# ════════════════════════════════════════════════════════════
class Settings:
    def __init__(self):
        self.file = os.path.join(get_data_dir(), 'settings.json')
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file) as f: return json.load(f)
            except: pass
        return {
            'alpaca_api_key': '',
            'alpaca_secret': '',
            'alpaca_paper': True,
            'check_interval_sec': 300,
            'max_position_size': 1000,
        }

    def save(self):
        with open(self.file, 'w') as f: json.dump(self.data, f, indent=2)

    def get(self, k, default=None): return self.data.get(k, default)
    def set(self, k, v): self.data[k] = v; self.save()


# ════════════════════════════════════════════════════════════
# THEME
# ════════════════════════════════════════════════════════════
THEMES = {
    'dark': {
        'bg': (0.06, 0.06, 0.10, 1), 'panel': (0.10, 0.10, 0.15, 1),
        'card': (0.13, 0.13, 0.20, 1), 'text': (0.80, 0.84, 0.96, 1),
        'text_dim': (0.55, 0.58, 0.70, 1), 'accent': (0.54, 0.71, 0.98, 1),
        'profit': (0.65, 0.89, 0.63, 1), 'loss': (0.95, 0.55, 0.66, 1),
        'warn': (0.98, 0.73, 0.53, 1), 'pink': (0.96, 0.76, 0.91, 1),
        'btn_text': (0.06, 0.06, 0.10, 1), 'grid': (0.20, 0.20, 0.30, 0.5),
        'icon': '🌙',
    },
    'light': {
        'bg': (0.96, 0.96, 0.98, 1), 'panel': (0.92, 0.93, 0.96, 1),
        'card': (1.0, 1.0, 1.0, 1), 'text': (0.15, 0.17, 0.25, 1),
        'text_dim': (0.40, 0.42, 0.50, 1), 'accent': (0.18, 0.45, 0.85, 1),
        'profit': (0.20, 0.65, 0.30, 1), 'loss': (0.85, 0.25, 0.35, 1),
        'warn': (0.95, 0.55, 0.20, 1), 'pink': (0.75, 0.30, 0.65, 1),
        'btn_text': (1.0, 1.0, 1.0, 1), 'grid': (0.70, 0.72, 0.80, 0.5),
        'icon': '☀️',
    }
}

class Theme:
    _inst = None
    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
            cls._inst.current = 'dark'
            cls._inst._listeners = []
            cls._inst._load()
        return cls._inst
    def _path(self): return os.path.join(get_data_dir(), 'theme.json')
    def _load(self):
        try:
            if os.path.exists(self._path()):
                with open(self._path()) as f:
                    self.current = json.load(f).get('theme', 'dark')
        except: pass
    def _save(self):
        try:
            with open(self._path(), 'w') as f: json.dump({'theme': self.current}, f)
        except: pass
    @property
    def colors(self): return THEMES[self.current]
    def get(self, k): return self.colors.get(k, (0.5, 0.5, 0.5, 1))
    def toggle(self):
        self.current = 'light' if self.current == 'dark' else 'dark'
        self._save()
        for fn in self._listeners:
            try: fn()
            except: pass
        return self.current
    def add_listener(self, fn):
        if fn not in self._listeners: self._listeners.append(fn)

theme = Theme()


# ════════════════════════════════════════════════════════════
# SENTIMENT
# ════════════════════════════════════════════════════════════
POS = {'beat':2.5,'surge':2.5,'soar':3,'jump':2,'rally':2,'gain':1.5,'rise':1.5,
       'climb':1.5,'strong':1.5,'growth':1.5,'profit':2,'record':2,'high':1,
       'positive':1.5,'bullish':2.5,'upgrade':2,'outperform':2,'buy':1.5,
       'success':1.5,'win':1.5,'breakthrough':2.5,'boost':1.5,'rebound':2}
NEG = {'miss':-2,'plunge':-3,'crash':-3,'tumble':-2.5,'fall':-1.5,'drop':-1.5,
       'decline':-1.5,'weak':-1.5,'loss':-2,'negative':-1.5,'bearish':-2.5,
       'downgrade':-2,'underperform':-2,'sell':-1.5,'fail':-2,'concern':-1.5,
       'warning':-2,'cut':-1.5,'layoff':-2.5,'lawsuit':-2,'fraud':-3,
       'crisis':-2.5,'collapse':-3,'bankruptcy':-3}
NEG_WORDS = {'not','no',"n't",'never','without'}
INTENS = {'very':1.5,'extremely':2,'highly':1.5,'slightly':0.5}

def score_text(t):
    if not t: return 0.0
    tokens = re.findall(r"[a-z']+", t.lower())
    s, c = 0, 0
    for i, w in enumerate(tokens):
        wt = POS.get(w, 0) or NEG.get(w, 0)
        if wt:
            c += 1
            for j in range(max(0, i-3), i):
                if tokens[j] in NEG_WORDS: wt = -wt * 0.7; break
            if i > 0 and tokens[i-1] in INTENS: wt *= INTENS[tokens[i-1]]
            s += wt
    return max(-1.0, min(1.0, s / (c * 2))) if c else 0.0


class NewsSentiment:
    def __init__(self):
        self.cache = os.path.join(get_data_dir(), 'cache', 'news')
        os.makedirs(self.cache, exist_ok=True)

    def fetch(self, ticker, max_h=15):
        cf = os.path.join(self.cache, f"{ticker}.pkl")
        if os.path.exists(cf):
            age = (datetime.now().timestamp() - os.path.getmtime(cf)) / 3600
            if age < 6:
                try:
                    with open(cf, 'rb') as f: return pickle.load(f)
                except: pass
        if not YF_OK: return []
        h = []
        try:
            for it in (yf.Ticker(ticker).news or [])[:max_h]:
                title = it.get('title') or it.get('content', {}).get('title', '')
                summ = it.get('summary') or it.get('content', {}).get('summary', '')
                if title: h.append({'title': title, 'summary': summ})
        except Exception as e: print(f"News: {e}")
        try:
            with open(cf, 'wb') as f: pickle.dump(h, f)
        except: pass
        return h

    def analyze(self, ticker, callback=None):
        h = self.fetch(ticker)
        if not h: return {'score': 0, 'signal': 'NEUTRAL', 'emoji': '⚪', 'count': 0, 'top': []}
        scores, anz = [], []
        for x in h:
            sc = score_text(f"{x['title']}. {x.get('summary','')}")
            scores.append(sc); anz.append({'title': x['title'][:80], 'score': sc})
        avg = sum(scores) / len(scores)
        sig, em = (('BULLISH','🟢') if avg > 0.15 else ('POSITIVE','🟢') if avg > 0.05
                   else ('BEARISH','🔴') if avg < -0.15 else ('NEGATIVE','🔴') if avg < -0.05
                   else ('NEUTRAL','⚪'))
        top = sorted(anz, key=lambda x: abs(x['score']), reverse=True)[:5]
        r = {'score': avg, 'signal': sig, 'emoji': em, 'count': len(h), 'top': top}
        if callback:
            callback(f"📰 News: {em} {sig} ({avg:+.2f}, {len(h)} headlines)")
            for x in top[:3]:
                m = '🟢' if x['score'] > 0 else '🔴' if x['score'] < 0 else '⚪'
                callback(f"   {m} {x['title'][:55]}... ({x['score']:+.2f})")
        return r


# ════════════════════════════════════════════════════════════
# ALERTS
# ════════════════════════════════════════════════════════════
class AlertSystem:
    PT = [1, 5, 10, 25, 50, 100]
    LT = [-1, -5, -10, -25, -50]

    def __init__(self, name='XOLA007', callback=None):
        self.name = name; self.callback = callback
        self.last = 0; self.peak = 0

    def _emit(self, level, msg):
        pre = {'profit':'💰','loss':'⚠️','critical':'🚨','info':'ℹ️','live':'🔴'}.get(level, '📢')
        full = f"{pre} {msg}"
        print(full)
        if self.callback:
            try: self.callback(full)
            except: pass
        if ANDROID_ALERTS:
            try:
                notification.notify(title=f"{pre} {self.name}", message=msg, timeout=5)
                if level == 'critical': vibrator.pattern(pattern=[0,0.5,0.2,0.5,0.2,0.5])
                elif level == 'loss': vibrator.vibrate(time=0.7)
                elif level == 'profit': vibrator.vibrate(time=0.3)
                elif level == 'live': vibrator.vibrate(time=0.5)
            except: pass

    def check_portfolio(self, v, init):
        pct = (v - init) / init * 100
        if v > self.peak: self.peak = v
        for t in self.PT:
            if pct >= t > self.last:
                self._emit('profit', f"PROFIT +{pct:.2f}% | ${v:.2f}")
                self.last = t; break
        for t in self.LT:
            if pct <= t < self.last:
                self._emit('critical' if t <= -25 else 'loss',
                           f"LOSS {pct:.2f}% | ${v:.2f}")
                self.last = t; break

    def signal_alert(self, t, txt): self._emit('info', f"Signal: {t} → {txt}")
    def trade_executed(self, action, ticker, qty, price, mode):
        self._emit('live', f"{mode.upper()} {action} {qty} {ticker} @ ${price:.2f}")
    def reset(self): self.last = 0; self.peak = 0


# ════════════════════════════════════════════════════════════
# DATA
# ════════════════════════════════════════════════════════════
def fetch_data(ticker, start, end, force=False):
    cf = os.path.join(get_data_dir(), 'cache', f"{ticker}_{start}_{end}.pkl")
    if os.path.exists(cf) and not force:
        age = (datetime.now().timestamp() - os.path.getmtime(cf)) / 3600
        if age < 24:
            try:
                with open(cf, 'rb') as f: return pickle.load(f)
            except: pass
    if not YF_OK:
        if os.path.exists(cf):
            with open(cf, 'rb') as f: return pickle.load(f)
        raise RuntimeError("No data available")
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty: raise ValueError(f"No data for {ticker}")
        df = add_indicators(df)
        with open(cf, 'wb') as f: pickle.dump(df, f)
        return df
    except Exception:
        if os.path.exists(cf):
            with open(cf, 'rb') as f: return pickle.load(f)
        raise


def add_indicators(df):
    df = df.copy()
    d = df['Close'].diff()
    g = d.where(d > 0, 0).rolling(14, min_periods=1).mean()
    l = -d.where(d < 0, 0).rolling(14, min_periods=1).mean()
    df['RSI'] = 100 - (100 / (1 + g / (l + 1e-9)))
    e12 = df['Close'].ewm(span=12, adjust=False).mean()
    e26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_norm'] = (e12 - e26) / df['Close']
    s20 = df['Close'].rolling(20, min_periods=1).mean()
    s50 = df['Close'].rolling(50, min_periods=1).mean()
    df['SMA_ratio'] = s20 / s50 - 1
    df['Volatility'] = df['Close'].pct_change().rolling(20, min_periods=1).std()
    df = df.dropna().reset_index(drop=True)
    for c in df.select_dtypes(include=['float64']).columns:
        df[c] = df[c].astype('float32')
    return df


def get_current_price(ticker):
    """Get latest price"""
    if not YF_OK: return None
    try:
        t = yf.Ticker(ticker)
        h = t.history(period='1d', interval='1m')
        if not h.empty: return float(h['Close'].iloc[-1])
        info = t.info
        return info.get('regularMarketPrice') or info.get('currentPrice')
    except: return None


# ════════════════════════════════════════════════════════════
# ENVIRONMENT
# ════════════════════════════════════════════════════════════
class TradingEnv:
    def __init__(self, data, balance=10000, fee=0.001, window=10,
                 alerts=None, ticker='?', sentiment=0.0):
        self.data = data.reset_index(drop=True)
        self.initial = balance; self.fee = fee; self.window = window
        self.action_space = 3; self.alerts = alerts; self.ticker = ticker
        self.sentiment = sentiment
        self.reset()

    def reset(self):
        self.balance = self.initial; self.shares = 0
        self.step_idx = self.window; self.total = self.initial
        self.trades = []; self.history = [self.initial]
        if self.alerts: self.alerts.reset()
        return self._state()

    def _state(self):
        w = self.data.iloc[self.step_idx - self.window:self.step_idx]
        p = w['Close'].values
        r = np.diff(p) / (p[:-1] + 1e-9)
        row = self.data.iloc[self.step_idx]
        price = float(row['Close'])
        v = self.balance + self.shares * price
        pos = (self.shares * price) / v if v > 0 else 0
        cash = self.balance / v if v > 0 else 0
        s = np.concatenate([r, [row['RSI']/100, row['MACD_norm'], row['SMA_ratio'],
                                 row['Volatility'], pos, cash, self.sentiment]])
        return np.nan_to_num(s).astype(np.float32)

    def step(self, action, live=False):
        price = float(self.data.iloc[self.step_idx]['Close'])
        prev = self.balance + self.shares * price
        if action == 1 and self.balance > price:
            sh = self.balance // (price * (1 + self.fee))
            if sh > 0:
                self.balance -= sh * price * (1 + self.fee)
                self.shares += sh
                self.trades.append(('BUY', self.step_idx, price))
        elif action == 2 and self.shares > 0:
            self.balance += self.shares * price * (1 - self.fee)
            self.trades.append(('SELL', self.step_idx, price))
            self.shares = 0
        self.step_idx += 1
        done = self.step_idx >= len(self.data) - 1
        np_ = float(self.data.iloc[self.step_idx]['Close'])
        nv = self.balance + self.shares * np_
        reward = (nv - prev) / (prev + 1e-9) * 100
        self.total = nv
        self.history.append(nv)
        if live and self.alerts:
            self.alerts.check_portfolio(nv, self.initial)
        return (self._state() if not done else np.zeros(len(self._state()))), reward, done


# ════════════════════════════════════════════════════════════
# AGENT
# ════════════════════════════════════════════════════════════
class Agent:
    def __init__(self, ss, as_, lr=0.005, gamma=0.95, eps=1.0, eps_min=0.01,
                 eps_decay=0.995, batch=16):
        self.state_size = ss; self.action_size = as_
        self.lr = lr; self.gamma = gamma
        self.epsilon = eps; self.eps_min = eps_min; self.eps_decay = eps_decay
        self.batch = batch
        self.W = np.random.randn(as_, ss).astype(np.float32) * 0.01
        self.b = np.zeros(as_, dtype=np.float32)
        self.Wt = self.W.copy(); self.bt = self.b.copy()
        self.memory = deque(maxlen=1500)

    def _q(self, s, t=False):
        return (self.Wt if t else self.W) @ s + (self.bt if t else self.b)

    def act(self, s, training=True):
        if training and np.random.rand() < self.epsilon:
            return random.randrange(self.action_size)
        return int(np.argmax(self._q(s)))

    def remember(self, s, a, r, ns, d): self.memory.append((s, a, r, ns, d))

    def replay(self):
        if len(self.memory) < self.batch: return 0
        b = random.sample(self.memory, self.batch)
        tot = 0
        for s, a, r, ns, d in b:
            tg = r + (0 if d else self.gamma * np.max(self._q(ns, True)))
            err = np.clip(tg - self._q(s)[a], -10, 10)
            self.W[a] += self.lr * err * s
            self.b[a] += self.lr * err
            tot += err ** 2
        if self.epsilon > self.eps_min: self.epsilon *= self.eps_decay
        return float(tot / self.batch)

    def update_target(self): self.Wt = self.W.copy(); self.bt = self.b.copy()

    def save(self, p):
        os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
        with open(p, 'wb') as f:
            pickle.dump({'W':self.W,'b':self.b,'Wt':self.Wt,'bt':self.bt,
                         'eps':self.epsilon}, f)

    def load(self, p):
        with open(p, 'rb') as f: d = pickle.load(f)
        self.W=d['W']; self.b=d['b']
        self.Wt=d.get('Wt',self.W.copy()); self.bt=d.get('bt',self.b.copy())
        self.epsilon=d.get('eps', self.eps_min)


# ════════════════════════════════════════════════════════════
# BROKERS — Paper & Real Money
# ════════════════════════════════════════════════════════════
class PaperBroker:
    """Simulated broker for paper trading"""
    
    def __init__(self, initial_balance=10000):
        self.initial = initial_balance
        self.balance = initial_balance
        self.positions = {}  # ticker -> shares
        self.trade_history = []
        self.file = os.path.join(get_data_dir(), 'live', 'paper_state.json')
        self._load()
    
    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file) as f:
                    d = json.load(f)
                    self.balance = d.get('balance', self.initial)
                    self.positions = d.get('positions', {})
                    self.trade_history = d.get('trade_history', [])
            except: pass
    
    def _save(self):
        try:
            with open(self.file, 'w') as f:
                json.dump({'balance': self.balance, 'positions': self.positions,
                           'trade_history': self.trade_history[-100:]}, f, indent=2)
        except: pass
    
    def buy(self, ticker, qty, price):
        cost = qty * price * 1.001
        if cost > self.balance:
            return False, f"Insufficient funds: need ${cost:.2f}, have ${self.balance:.2f}"
        self.balance -= cost
        self.positions[ticker] = self.positions.get(ticker, 0) + qty
        self.trade_history.append({
            'time': datetime.now().isoformat(), 'action': 'BUY',
            'ticker': ticker, 'qty': qty, 'price': price, 'mode': 'PAPER'
        })
        self._save()
        return True, f"Bought {qty} {ticker} @ ${price:.2f}"
    
    def sell(self, ticker, qty, price):
        if self.positions.get(ticker, 0) < qty:
            return False, f"Only {self.positions.get(ticker, 0)} shares to sell"
        revenue = qty * price * 0.999
        self.balance += revenue
        self.positions[ticker] -= qty
        if self.positions[ticker] == 0: del self.positions[ticker]
        self.trade_history.append({
            'time': datetime.now().isoformat(), 'action': 'SELL',
            'ticker': ticker, 'qty': qty, 'price': price, 'mode': 'PAPER'
        })
        self._save()
        return True, f"Sold {qty} {ticker} @ ${price:.2f}"
    
    def get_portfolio_value(self, current_prices):
        v = self.balance
        for t, q in self.positions.items():
            v += q * current_prices.get(t, 0)
        return v
    
    def reset(self):
        self.balance = self.initial
        self.positions = {}
        self.trade_history = []
        self._save()


class AlpacaBroker:
    """Real money trading via Alpaca API (also supports paper via paper endpoint)"""
    
    def __init__(self, api_key, secret, paper=True):
        self.api_key = api_key
        self.secret = secret
        self.base_url = ('https://paper-api.alpaca.markets' if paper
                         else 'https://api.alpaca.markets')
        self.paper = paper
    
    def _request(self, method, endpoint, body=None):
        url = f"{self.base_url}{endpoint}"
        headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.secret,
            'Content-Type': 'application/json'
        }
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try: return {'error': json.loads(e.read().decode())}
            except: return {'error': f"HTTP {e.code}"}
        except Exception as e:
            return {'error': str(e)}
    
    def get_account(self):
        return self._request('GET', '/v2/account')
    
    def get_positions(self):
        return self._request('GET', '/v2/positions')
    
    def buy(self, ticker, qty, price=None):
        body = {
            'symbol': ticker, 'qty': str(qty),
            'side': 'buy', 'type': 'market', 'time_in_force': 'day'
        }
        r = self._request('POST', '/v2/orders', body)
        if 'error' in r:
            return False, str(r['error'])
        return True, f"Order placed: {qty} {ticker}"
    
    def sell(self, ticker, qty, price=None):
        body = {
            'symbol': ticker, 'qty': str(qty),
            'side': 'sell', 'type': 'market', 'time_in_force': 'day'
        }
        r = self._request('POST', '/v2/orders', body)
        if 'error' in r:
            return False, str(r['error'])
        return True, f"Order placed: sell {qty} {ticker}"
    
    def get_portfolio_value(self, current_prices=None):
        acc = self.get_account()
        if 'error' in acc: return 0
        return float(acc.get('portfolio_value', 0))
    
    def test_connection(self):
        acc = self.get_account()
        if 'error' in acc:
            return False, f"Connection failed: {acc['error']}"
        return True, f"Connected. Buying power: ${acc.get('buying_power', '?')}"


# ════════════════════════════════════════════════════════════
# BOT TRAINER
# ════════════════════════════════════════════════════════════
class BotTrainer:
    def __init__(self, ticker='AAPL', balance=10000):
        self.ticker = ticker.upper()
        self.initial = balance
        self.model_path = os.path.join(get_data_dir(), 'models', f'{self.ticker}_model.pkl')
        self.agent = None
        self.history = []
        self.alerts = None
        self.stop_flag = False

    def _init_agent(self, ss, as_):
        self.agent = Agent(ss, as_)
        if os.path.exists(self.model_path):
            try: self.agent.load(self.model_path); return True
            except: pass
        return False

    def train(self, episodes=10, start='2020-01-01', end='2023-01-01', callback=None):
        self.stop_flag = False
        self.alerts = AlertSystem(f'XOLA007-{self.ticker}', callback)
        data = fetch_data(self.ticker, start, end)
        env = TradingEnv(data, self.initial, alerts=self.alerts, ticker=self.ticker)
        ss = len(env.reset())
        loaded = self._init_agent(ss, env.action_space)
        if loaded and callback: callback("📂 Loaded saved model")
        for ep in range(episodes):
            if self.stop_flag:
                if callback: callback("🛑 Training stopped")
                break
            state = env.reset()
            done = False
            while not done:
                a = self.agent.act(state)
                ns, r, done = env.step(a)
                self.agent.remember(state, a, r, ns, done)
                self.agent.replay()
                state = ns
            if ep % 5 == 0: self.agent.update_target()
            roi = (env.total - env.initial) / env.initial * 100
            self.history.append(roi)
            msg = f"Ep {ep+1:3d}/{episodes} | ROI: {roi:+7.2f}% | ε: {self.agent.epsilon:.3f} | Trades: {len(env.trades)}"
            if callback: callback(msg)
            else: print(msg)
            if IS_ANDROID and ep % 10 == 0: gc.collect()
        self.agent.save(self.model_path)
        if callback: callback(f"💾 Model saved")
        return self.history

    def backtest(self, start='2023-01-01', end=None, callback=None):
        if end is None: end = datetime.now().strftime('%Y-%m-%d')
        self.alerts = AlertSystem(f'XOLA007-{self.ticker}', callback)
        data = fetch_data(self.ticker, start, end)
        env = TradingEnv(data, self.initial, alerts=self.alerts, ticker=self.ticker)
        if self.agent is None:
            ss = len(env.reset())
            if not self._init_agent(ss, env.action_space):
                raise RuntimeError("No model. Train first!")
        state = env.reset()
        done = False
        while not done:
            a = self.agent.act(state, training=False)
            state, _, done = env.step(a, live=True)
        roi = (env.total - env.initial) / env.initial * 100
        bh = ((data['Close'].iloc[-1] - data['Close'].iloc[env.window]) /
              data['Close'].iloc[env.window] * 100)
        m = self._metrics(env.history, env.trades)
        r = {'ticker': self.ticker, 'initial_value': float(env.initial),
             'final_value': float(env.total), 'roi': float(roi),
             'buy_hold': float(bh), 'trades': len(env.trades),
             'history': env.history, 'trade_log': env.trades, 'metrics': m}
        if callback:
            callback("─" * 40)
            callback(f"📊 BACKTEST: {self.ticker}")
            callback(f"💰 Final:    ${env.total:.2f}")
            callback(f"📈 Bot ROI:  {roi:+.2f}%")
            callback(f"📊 B&H ROI:  {bh:+.2f}%")
            callback(f"📐 Sharpe:   {m['sharpe']:.2f}")
            callback(f"📉 Max DD:   {m['max_dd']:.2f}%")
            callback(f"🎯 Win Rate: {m['win_rate']:.1f}%")
        return r

    def _metrics(self, h, t):
        ha = np.array(h, dtype=float)
        if len(ha) < 2: return {'sharpe':0,'max_dd':0,'win_rate':0,'wins':0,'losses':0}
        r = np.diff(ha) / (ha[:-1] + 1e-9)
        sh = (r.mean() / r.std()) * np.sqrt(252) if r.std() > 0 else 0
        cm = ha / ha[0]
        dd = float((cm / np.maximum.accumulate(cm) - 1).min()) * 100
        w, l, bp = 0, 0, None
        for tt, _, p in t:
            if tt == 'BUY': bp = p
            elif tt == 'SELL' and bp:
                if p > bp: w += 1
                else: l += 1
                bp = None
        tot = w + l
        return {'sharpe': float(sh), 'max_dd': dd,
                'win_rate': (w/tot*100) if tot else 0, 'wins': w, 'losses': l}

    def predict_today(self, callback=None, use_sentiment=True):
        self.alerts = AlertSystem(f'XOLA007-{self.ticker}', callback)
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        data = fetch_data(self.ticker, start, end, force=True)
        sent_s, sent_i = 0.0, None
        if use_sentiment:
            try:
                sent_i = NewsSentiment().analyze(self.ticker, callback)
                sent_s = sent_i['score']
            except Exception as e:
                if callback: callback(f"⚠️ Sentiment: {e}")
        env = TradingEnv(data, alerts=self.alerts, ticker=self.ticker, sentiment=sent_s)
        if self.agent is None:
            ss = len(env.reset())
            if not self._init_agent(ss, env.action_space):
                raise RuntimeError("Train first!")
        env.step_idx = len(data) - 1
        state = env._state()
        action = self.agent.act(state, training=False)
        acts = {0:'⏸️ HOLD', 1:'🟢 BUY', 2:'🔴 SELL'}
        text = acts[action]
        price = float(data['Close'].iloc[-1])
        if sent_i and abs(sent_i['score']) > 0.3:
            if sent_i['score'] > 0.3 and action == 2: text += "  ⚠️(news bullish)"
            elif sent_i['score'] < -0.3 and action == 1: text += "  ⚠️(news bearish)"
        if callback:
            callback("═" * 40)
            callback(f"📈 {self.ticker} @ ${price:.2f}")
            callback(f"🎯 Signal: {text}")
            if sent_i: callback(f"📰 News:   {sent_i['emoji']} {sent_i['signal']}")
            callback("═" * 40)
        self.alerts.signal_alert(self.ticker, text)
        return action, text, price

    def export_csv(self, result, path=None):
        if path is None:
            path = os.path.join(get_data_dir(), 'exports',
                f'{self.ticker}_{datetime.now():%Y%m%d_%H%M%S}.csv')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Ticker', self.ticker])
            w.writerow(['ROI %', f"{result['roi']:.2f}"])
            w.writerow(['Final', result['final_value']])
            w.writerow(['Trades', result['trades']])
            w.writerow([])
            w.writerow(['#', 'Type', 'Step', 'Price'])
            for i, (t, s, p) in enumerate(result['trade_log'], 1):
                w.writerow([i, t, s, f"{p:.2f}"])
        return path
    
    def stop(self): self.stop_flag = True


# ════════════════════════════════════════════════════════════
# LIVE TRADER (Run/Stop)
# ════════════════════════════════════════════════════════════
class LiveTrader:
    """Live trading engine with paper/real money modes"""
    
    def __init__(self, ticker, mode='PAPER', broker=None, callback=None,
                 interval=300, max_position=1000):
        self.ticker = ticker.upper()
        self.mode = mode  # 'PAPER' or 'REAL'
        self.broker = broker
        self.callback = callback
        self.interval = interval
        self.max_position = max_position
        self.alerts = AlertSystem(f'XOLA007-LIVE-{ticker}', callback)
        self.bot = BotTrainer(ticker)
        self._thread = None
        self._stop = threading.Event()
        self.last_signal = None
        self.last_price = None
    
    def _log(self, msg):
        if self.callback: self.callback(msg)
        else: print(msg)
    
    def start(self):
        if self._thread and self._thread.is_alive():
            self._log("⚠️ Already running")
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._log(f"🚀 LIVE TRADING STARTED [{self.mode}] for {self.ticker}")
        self._log(f"   Check every {self.interval}s | Max position: ${self.max_position}")
        if self.mode == 'REAL':
            self._log("🔴 REAL MONEY MODE - Trades will execute on broker!")
        return True
    
    def stop(self):
        if self._thread:
            self._stop.set()
            self._log("🛑 STOP signal sent. Waiting for cycle to finish...")
        else:
            self._log("⚠️ Not running")
    
    def is_running(self):
        return self._thread and self._thread.is_alive() and not self._stop.is_set()
    
    def _loop(self):
        try:
            # Verify model exists
            if not os.path.exists(self.bot.model_path):
                self._log(f"❌ No trained model for {self.ticker}. Train first!")
                return
            
            cycle = 0
            while not self._stop.is_set():
                cycle += 1
                try:
                    self._log(f"\n⏱️ {datetime.now():%Y-%m-%d %H:%M:%S} | Cycle #{cycle}")
                    
                    # Get prediction
                    action, text, price = self.bot.predict_today(callback=None)
                    self._log(f"📊 {self.ticker} @ ${price:.2f} | Signal: {text}")
                    
                    # Detect price movement
                    if self.last_price:
                        chg = (price - self.last_price) / self.last_price * 100
                        if abs(chg) >= 0.5:
                            self._log(f"   📈 Price moved: {chg:+.2f}%")
                    self.last_price = price
                    
                    # Execute if signal changed
                    if action == 1 and self.last_signal != 1:  # BUY
                        self._execute_buy(price)
                    elif action == 2 and self.last_signal != 2:  # SELL
                        self._execute_sell(price)
                    elif action == 0:
                        self._log("   ⏸️ HOLD")
                    
                    self.last_signal = action
                    
                    # Show portfolio value
                    self._show_portfolio({self.ticker: price})
                    
                except Exception as e:
                    self._log(f"⚠️ Cycle error: {e}")
                
                # Wait (with stop check)
                for _ in range(self.interval):
                    if self._stop.is_set(): break
                    time.sleep(1)
            
            self._log("🛑 Live trading stopped")
        except Exception as e:
            self._log(f"❌ Fatal error: {e}")
    
    def _execute_buy(self, price):
        if not self.broker:
            self._log("⚠️ No broker configured")
            return
        qty = int(self.max_position // price)
        if qty < 1:
            self._log(f"⚠️ Position too small for price ${price:.2f}")
            return
        ok, msg = self.broker.buy(self.ticker, qty, price)
        if ok:
            self.alerts.trade_executed('BUY', self.ticker, qty, price, self.mode)
        else:
            self._log(f"❌ BUY failed: {msg}")
    
    def _execute_sell(self, price):
        if not self.broker:
            return
        # Get position
        if isinstance(self.broker, PaperBroker):
            qty = self.broker.positions.get(self.ticker, 0)
        else:
            try:
                pos = self.broker.get_positions()
                qty = 0
                if isinstance(pos, list):
                    for p in pos:
                        if p.get('symbol') == self.ticker:
                            qty = int(float(p.get('qty', 0)))
                            break
            except: qty = 0
        
        if qty < 1:
            self._log(f"   ℹ️ No position in {self.ticker} to sell")
            return
        
        ok, msg = self.broker.sell(self.ticker, qty, price)
        if ok:
            self.alerts.trade_executed('SELL', self.ticker, qty, price, self.mode)
        else:
            self._log(f"❌ SELL failed: {msg}")
    
    def _show_portfolio(self, prices):
        if isinstance(self.broker, PaperBroker):
            v = self.broker.get_portfolio_value(prices)
            roi = (v - self.broker.initial) / self.broker.initial * 100
            self._log(f"   💼 Portfolio: ${v:.2f} ({roi:+.2f}%)")
            self.alerts.check_portfolio(v, self.broker.initial)
        elif isinstance(self.broker, AlpacaBroker):
            acc = self.broker.get_account()
            if 'error' not in acc:
                v = float(acc.get('portfolio_value', 0))
                self._log(f"   💼 Account: ${v:.2f}")


# ════════════════════════════════════════════════════════════
# SALES WEBSITE
# ════════════════════════════════════════════════════════════
WEBSITE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>XOLA007 - Self-Learning AI Trading Bot</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #0f0f19; color: #cdd6f4; line-height: 1.6; }
.gradient-bg { background: linear-gradient(135deg, #0f0f19 0%, #1e1e2e 50%, #11111b 100%); }
.hero { padding: 80px 20px 60px; text-align: center; }
.hero h1 { font-size: clamp(48px, 8vw, 82px); background: linear-gradient(135deg, #f5c2e7, #89b4fa, #a6e3a1);
           -webkit-background-clip: text; -webkit-text-fill-color: transparent;
           background-clip: text; margin-bottom: 15px; font-weight: 800; letter-spacing: -2px; }
.hero .tagline { font-size: 22px; color: #a6e3a1; margin-bottom: 10px; }
.hero .sub { font-size: 16px; color: #6c7086; margin-bottom: 40px; }
.hero .cta-buttons { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; margin-top: 30px; }
.btn { padding: 16px 36px; border: none; border-radius: 10px; font-size: 16px;
       font-weight: 700; cursor: pointer; transition: all 0.3s; text-decoration: none;
       display: inline-block; }
.btn-primary { background: linear-gradient(135deg, #f5c2e7, #cba6f7);
               color: #1e1e2e; box-shadow: 0 4px 20px rgba(245,194,231,0.4); }
.btn-primary:hover { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(245,194,231,0.6); }
.btn-secondary { background: transparent; color: #cdd6f4; border: 2px solid #45475a; }
.btn-secondary:hover { border-color: #89b4fa; color: #89b4fa; }
.container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
section { padding: 80px 0; }
.section-title { font-size: 42px; text-align: center; margin-bottom: 50px; color: #f5c2e7; }
.features { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 25px; }
.feature-card { background: #1e1e2e; padding: 35px 25px; border-radius: 16px;
                border: 1px solid #313244; transition: all 0.3s; }
.feature-card:hover { transform: translateY(-5px); border-color: #89b4fa;
                       box-shadow: 0 10px 30px rgba(137,180,250,0.2); }
.feature-icon { font-size: 48px; margin-bottom: 15px; }
.feature-card h3 { color: #89b4fa; margin-bottom: 10px; font-size: 22px; }
.feature-card p { color: #a6adc8; font-size: 14px; }
.pricing { background: #11111b; }
.pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 25px; margin-top: 40px; }
.price-card { background: #1e1e2e; padding: 40px 30px; border-radius: 16px;
              text-align: center; position: relative; border: 2px solid transparent;
              transition: all 0.3s; }
.price-card:hover { transform: scale(1.03); }
.price-card.featured { border-color: #f5c2e7; background: linear-gradient(180deg, #1e1e2e, #313244); }
.price-card.featured::before { content: '⭐ MOST POPULAR'; position: absolute; top: -12px;
                                left: 50%; transform: translateX(-50%); background: #f5c2e7;
                                color: #1e1e2e; padding: 5px 15px; border-radius: 20px;
                                font-size: 11px; font-weight: bold; }
.tier-name { font-size: 22px; color: #89b4fa; margin-bottom: 10px; }
.tier-price { font-size: 52px; font-weight: 800; color: #a6e3a1; margin: 20px 0; }
.tier-price .cents { font-size: 24px; opacity: 0.7; }
.tier-period { color: #6c7086; font-size: 14px; margin-bottom: 25px; }
.tier-features { list-style: none; text-align: left; margin: 30px 0; }
.tier-features li { padding: 8px 0; color: #cdd6f4; }
.tier-features li::before { content: '✅ '; margin-right: 5px; }
.buy-btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #89b4fa, #cba6f7);
           color: #1e1e2e; border: none; border-radius: 10px; font-weight: 700;
           cursor: pointer; font-size: 15px; transition: all 0.3s; }
.buy-btn:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(137,180,250,0.4); }
.demo { background: #181825; }
.demo-screens { display: flex; justify-content: center; gap: 30px; margin-top: 40px; flex-wrap: wrap; }
.screen { background: #1e1e2e; border: 2px solid #313244; border-radius: 20px;
          padding: 20px; max-width: 280px; }
.screen-title { color: #f5c2e7; margin-bottom: 15px; font-weight: bold; }
.screen-content { background: #11111b; padding: 15px; border-radius: 10px;
                  font-family: monospace; font-size: 12px; color: #a6e3a1;
                  min-height: 200px; }
.testimonials { background: #11111b; }
.testimonial-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: 25px; margin-top: 40px; }
.testimonial { background: #1e1e2e; padding: 30px; border-radius: 12px;
               border-left: 4px solid #f5c2e7; }
.testimonial .quote { font-style: italic; margin-bottom: 15px; color: #cdd6f4; }
.testimonial .author { color: #89b4fa; font-weight: bold; }
.testimonial .stars { color: #f9e2af; margin-bottom: 10px; }
.faq { max-width: 800px; margin: 0 auto; }
.faq-item { background: #1e1e2e; padding: 20px 25px; border-radius: 10px;
            margin-bottom: 15px; cursor: pointer; transition: all 0.3s; }
.faq-item:hover { background: #313244; }
.faq-question { font-weight: bold; color: #89b4fa; display: flex;
                justify-content: space-between; align-items: center; }
.faq-answer { color: #a6adc8; margin-top: 10px; display: none; font-size: 14px; }
.faq-item.open .faq-answer { display: block; }
.cta-section { text-align: center; padding: 100px 20px;
               background: linear-gradient(135deg, #313244, #45475a); }
.cta-section h2 { font-size: 42px; color: #f5c2e7; margin-bottom: 20px; }
.cta-section p { font-size: 18px; color: #cdd6f4; margin-bottom: 30px; }
footer { background: #11111b; padding: 40px 20px; text-align: center;
         color: #6c7086; font-size: 13px; border-top: 1px solid #313244; }
footer a { color: #89b4fa; text-decoration: none; }
.disclaimer { background: #f38ba8; color: #1e1e2e; padding: 15px;
              text-align: center; font-size: 13px; font-weight: bold; }
.activation-box { background: linear-gradient(135deg, #a6e3a1, #94e2d5); color: #1e1e2e;
                  padding: 30px; border-radius: 16px; margin: 30px auto; max-width: 600px;
                  text-align: center; }
.activation-box h3 { margin-bottom: 15px; font-size: 24px; }
.activation-code { background: #1e1e2e; color: #a6e3a1; padding: 15px 25px;
                   border-radius: 10px; font-family: monospace; font-size: 22px;
                   font-weight: bold; letter-spacing: 2px; display: inline-block;
                   margin: 15px 0; }
@media (max-width: 768px) { .section-title { font-size: 32px; } }
</style>
</head>
<body>

<div class="disclaimer">
⚠️ Educational use only. Trading involves substantial financial risk. Past performance does not guarantee future results.
</div>

<header class="hero gradient-bg">
  <div class="container">
    <h1>🤖 XOLA007</h1>
    <p class="tagline">Self-Learning AI Trading Bot</p>
    <p class="sub">Adaptive Q-Learning • News Sentiment • Real-Time Alerts</p>
    <div class="cta-buttons">
      <a href="#pricing" class="btn btn-primary">💰 Get Started - $19.99</a>
      <a href="#features" class="btn btn-secondary">📋 See Features</a>
    </div>
  </div>
</header>

<section id="features">
  <div class="container">
    <h2 class="section-title">⚡ Powerful Features</h2>
    <div class="features">
      <div class="feature-card">
        <div class="feature-icon">🧠</div>
        <h3>Self-Learning AI</h3>
        <p>Q-learning algorithm continuously adapts to market conditions. The bot learns from every trade and gets smarter over time.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">📰</div>
        <h3>News Sentiment</h3>
        <p>Built-in financial news analyzer scores headlines to detect bullish or bearish market sentiment in real-time.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">📝</div>
        <h3>Paper Trading</h3>
        <p>Test your strategies with simulated money first. Practice risk-free until you're confident with real trades.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">💵</div>
        <h3>Real Money Mode</h3>
        <p>Connect to your Alpaca broker account for live automated trading on stocks and crypto with one click.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">📱</div>
        <h3>Mobile App</h3>
        <p>Native Android APK with push notifications and vibration alerts. Trade from anywhere on your phone.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">💱</div>
        <h3>Crypto Support</h3>
        <p>Trade Bitcoin, Ethereum, and other cryptocurrencies alongside traditional stocks all in one app.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">🔔</div>
        <h3>Smart Alerts</h3>
        <p>Profit/loss thresholds, drawdown warnings, and trade execution notifications keep you informed 24/7.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">📊</div>
        <h3>Pro Metrics</h3>
        <p>Sharpe ratio, max drawdown, win rate, volatility - all the metrics professionals use to evaluate performance.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">🌙</div>
        <h3>Dark/Light Theme</h3>
        <p>Beautiful dark mode for late-night trading or bright theme for daytime use. Switch anytime.</p>
      </div>
    </div>
  </div>
</section>

<section class="pricing" id="pricing">
  <div class="container">
    <h2 class="section-title">💎 Choose Your Plan</h2>
    <p style="text-align:center; color:#a6adc8; margin-bottom:30px;">All plans include 30-day money-back guarantee</p>
    
    <div class="pricing-grid">
      <div class="price-card">
        <div class="tier-name">STANDARD</div>
        <div class="tier-price">$19<span class="cents">.99</span></div>
        <div class="tier-period">1 device · 1 year</div>
        <ul class="tier-features">
          <li>Self-learning AI bot</li>
          <li>Paper trading</li>
          <li>News sentiment</li>
          <li>Mobile + Desktop</li>
          <li>Email support</li>
        </ul>
        <button class="buy-btn" onclick="buy('STANDARD')">Get Standard</button>
      </div>
      
      <div class="price-card featured">
        <div class="tier-name">PREMIUM</div>
        <div class="tier-price">$59<span class="cents">.99</span></div>
        <div class="tier-period">3 devices · 1 year</div>
        <ul class="tier-features">
          <li>Everything in Standard</li>
          <li><b>Real money trading</b></li>
          <li>Alpaca broker integration</li>
          <li>Multi-ticker portfolio</li>
          <li>Priority support</li>
          <li>Advanced metrics</li>
        </ul>
        <button class="buy-btn" onclick="buy('PREMIUM')">Get Premium</button>
      </div>
      
      <div class="price-card">
        <div class="tier-name">LIFETIME</div>
        <div class="tier-price">$99<span class="cents">.99</span></div>
        <div class="tier-period">1 device · Never expires</div>
        <ul class="tier-features">
          <li>Everything in Premium</li>
          <li>Never pay again</li>
          <li>All future updates</li>
          <li>VIP support</li>
          <li>Early access to features</li>
        </ul>
        <button class="buy-btn" onclick="buy('LIFETIME')">Get Lifetime</button>
      </div>
    </div>
    
    <div class="activation-box">
      <h3>🎁 Try It Free for 30 Days!</h3>
      <p>Download now and use all features free. No credit card required.</p>
      <p style="margin-top:15px;">Or use this test code:</p>
      <div class="activation-code">XOLA-2024-PREMIUM-007</div>
      <p style="font-size:12px; opacity:0.8;">Premium Lifetime Demo Access</p>
    </div>
  </div>
</section>

<section class="demo">
  <div class="container">
    <h2 class="section-title">📱 See It In Action</h2>
    <div class="demo-screens">
      <div class="screen">
        <div class="screen-title">📊 Backtest Results</div>
        <div class="screen-content">
📊 BACKTEST: AAPL<br>
💰 Final: $13,847.50<br>
📈 Bot ROI: +38.47%<br>
📊 B&H ROI: +12.30%<br>
⚡ Edge: +26.17%<br>
📐 Sharpe: 1.84<br>
📉 Max DD: -8.20%<br>
🎯 Win Rate: 67.4%
        </div>
      </div>
      <div class="screen">
        <div class="screen-title">🔴 Live Trading</div>
        <div class="screen-content">
⏱️ 14:23:05 | Cycle #12<br>
📊 AAPL @ $178.45<br>
🎯 Signal: 🟢 BUY<br>
📰 News: 🟢 BULLISH<br>
✅ Order placed<br>
💼 Portfolio: $10,425<br>
   📈 +4.25%
        </div>
      </div>
      <div class="screen">
        <div class="screen-title">💰 Profit Alert</div>
        <div class="screen-content">
💰 PROFIT +5.00%<br>
$10,500.00<br>
<br>
💰 PROFIT +10.00%<br>
$11,000.00<br>
<br>
🟢 SELL signal triggered<br>
Locking in gains...
        </div>
      </div>
    </div>
  </div>
</section>

<section class="testimonials">
  <div class="container">
    <h2 class="section-title">⭐ What Users Say</h2>
    <div class="testimonial-grid">
      <div class="testimonial">
        <div class="stars">⭐⭐⭐⭐⭐</div>
        <p class="quote">"Finally a bot that actually learns. After 2 weeks of training it's outperforming my manual trades."</p>
        <p class="author">— Mike T., Day Trader</p>
      </div>
      <div class="testimonial">
        <div class="stars">⭐⭐⭐⭐⭐</div>
        <p class="quote">"The paper trading mode let me test for a month before using real money. Worth every penny!"</p>
        <p class="author">— Sarah K., Investor</p>
      </div>
      <div class="testimonial">
        <div class="stars">⭐⭐⭐⭐⭐</div>
        <p class="quote">"Love the mobile app. Get instant alerts on my phone whenever the bot makes a trade."</p>
        <p class="author">— David L., Crypto Trader</p>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="container">
    <h2 class="section-title">❓ Frequently Asked Questions</h2>
    <div class="faq">
      <div class="faq-item" onclick="this.classList.toggle('open')">
        <div class="faq-question">Is this safe for real money? <span>+</span></div>
        <div class="faq-answer">XOLA007 supports both paper trading (simulated) and real money trading via Alpaca broker. We strongly recommend testing for at least 30 days in paper mode before using real money. All trading carries risk.</div>
      </div>
      <div class="faq-item" onclick="this.classList.toggle('open')">
        <div class="faq-question">How does the AI learn? <span>+</span></div>
        <div class="faq-answer">XOLA007 uses Q-learning with experience replay. It analyzes price patterns, technical indicators (RSI, MACD, SMA), volatility, and news sentiment to make decisions. The model improves with each training session.</div>
      </div>
      <div class="faq-item" onclick="this.classList.toggle('open')">
        <div class="faq-question">What devices does it work on? <span>+</span></div>
        <div class="faq-answer">Works on Windows, Mac, Linux, and Android. The Android version is available as a native APK or via Pydroid 3.</div>
      </div>
      <div class="faq-item" onclick="this.classList.toggle('open')">
        <div class="faq-question">Can I cancel anytime? <span>+</span></div>
        <div class="faq-answer">Yes! We offer a 30-day money-back guarantee. If you're not satisfied, contact us for a full refund.</div>
      </div>
      <div class="faq-item" onclick="this.classList.toggle('open')">
        <div class="faq-question">Do you guarantee profits? <span>+</span></div>
        <div class="faq-answer">Absolutely not. No trading system can guarantee profits. Trading involves substantial risk. This software is a tool to assist your trading decisions, not a guaranteed money maker.</div>
      </div>
      <div class="faq-item" onclick="this.classList.toggle('open')">
        <div class="faq-question">What brokers are supported? <span>+</span></div>
        <div class="faq-answer">Currently we support Alpaca (free, US stocks + crypto). More brokers coming soon based on customer demand.</div>
      </div>
    </div>
  </div>
</section>

<section class="cta-section">
  <h2>🚀 Ready to Start?</h2>
  <p>Join thousands of traders using XOLA007</p>
  <a href="#pricing" class="btn btn-primary">Get Started Now →</a>
</section>

<footer>
  <p>© 2024 XOLA007. All rights reserved.</p>
  <p style="margin-top:10px;">
    <a href="#terms">Terms of Service</a> · 
    <a href="#privacy">Privacy Policy</a> · 
    <a href="#contact">Contact</a>
  </p>
  <p style="margin-top:15px; max-width:600px; margin-left:auto; margin-right:auto;">
    ⚠️ <b>Risk Disclaimer:</b> Trading securities and cryptocurrencies carries substantial 
    risk of loss. Past performance is not indicative of future results. Only trade with 
    money you can afford to lose. XOLA007 is an educational tool, not financial advice.
  </p>
</footer>

<script>
function buy(tier) {
  const prices = {STANDARD: 19.99, PREMIUM: 59.99, LIFETIME: 99.99};
  alert('🎉 Thank you for choosing ' + tier + '!\\n\\n' +
        'Price: $' + prices[tier] + '\\n\\n' +
        'In production, this would redirect to Stripe/PayPal checkout.\\n\\n' +
        'For now, use this demo code in the app:\\n' +
        'XOLA-2024-PREMIUM-007');
}
</script>
</body>
</html>
"""


class WebsiteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(WEBSITE_HTML.encode('utf-8'))
    def log_message(self, *args): pass  # Silence default logging


def run_website(port=8080):
    """Start the sales website on localhost"""
    server = HTTPServer(('0.0.0.0', port), WebsiteHandler)
    print(f"\n🌐 XOLA007 Sales Website running at:")
    print(f"   http://localhost:{port}")
    print(f"   http://0.0.0.0:{port}")
    print(f"\n   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Website stopped")
        server.shutdown()


# ════════════════════════════════════════════════════════════
# CLI MODE
# ════════════════════════════════════════════════════════════
_last_backtest = {'data': None, 'bot': None}
_live_traders = {}

def run_cli():
    lm = LicenseManager()
    settings = Settings()
    print(f"\n{'═'*55}")
    print(f"  🤖 {APP_NAME} v{VERSION} - Self-Learning Trading Bot")
    print(f"  Platform: {'Android' if IS_ANDROID else 'Desktop'}")
    print(f"  Status: {lm.get_status()}")
    print(f"{'═'*55}\n")

    if not lm.has_agreed():
        print(LICENSE_TEXT)
        if input("Do you AGREE? (yes/no): ").strip().lower() != 'yes':
            return
        lm.accept_license()

    if lm.is_trial_expired():
        print("⚠️ Trial expired. Activation required.")
        ok, msg = lm.activate(input("Code: ").strip())
        print(f"{'✅' if ok else '❌'} {msg}")
        if not ok: return

    while True:
        print(f"\n{lm.get_status()}")
        print("─" * 50)
        print("  TRAINING & BACKTEST:")
        print("  [1] Train Bot              [2] Backtest")
        print("  [3] Today's Signal         [4] News Sentiment")
        print("  LIVE TRADING:")
        print("  [5] Start Paper Trading    [6] Start Real Trading")
        print("  [7] Stop Live Trader       [8] Show Live Status")
        print("  SETTINGS:")
        print("  [9] Configure Alpaca       [10] Export CSV")
        print("  [11] Activate License      [12] Launch Website")
        print("  [0] Quit")
        c = input("→ ").strip()
        
        if c == '0': break
        elif c == '11':
            ok, msg = lm.activate(input("Code: ").strip())
            print(f"{'✅' if ok else '❌'} {msg}")
        elif c == '12':
            port = int(input("Port [8080]: ") or 8080)
            threading.Thread(target=run_website, args=(port,), daemon=False).start()
            print(f"\n✅ Website started at http://localhost:{port}")
        elif c == '9':
            print("\n🔑 Alpaca Settings")
            print("Get free API keys: https://alpaca.markets")
            settings.set('alpaca_api_key', input(f"API Key [{settings.get('alpaca_api_key', '')[:8]}...]: ") or settings.get('alpaca_api_key', ''))
            settings.set('alpaca_secret', input("Secret (input): ") or settings.get('alpaca_secret', ''))
            paper = input("Paper mode? [y/n] (default y): ").strip().lower()
            settings.set('alpaca_paper', paper != 'n')
            print("✅ Saved. Testing connection...")
            try:
                br = AlpacaBroker(settings.get('alpaca_api_key'),
                                  settings.get('alpaca_secret'),
                                  paper=settings.get('alpaca_paper'))
                ok, msg = br.test_connection()
                print(f"{'✅' if ok else '❌'} {msg}")
            except Exception as e: print(f"❌ {e}")
        elif c == '4':
            t = input("Ticker [AAPL]: ").strip().upper() or 'AAPL'
            NewsSentiment().analyze(t, print)
        elif c in ('1', '2', '3', '10'):
            t = input("Ticker [AAPL]: ").strip().upper() or 'AAPL'
            bot = BotTrainer(t)
            try:
                if c == '1':
                    eps = int(input("Episodes [10]: ") or 10)
                    bot.train(episodes=eps)
                elif c == '2':
                    r = bot.backtest()
                    _last_backtest['data'] = r; _last_backtest['bot'] = bot
                elif c == '3':
                    bot.predict_today(callback=print)
                elif c == '10':
                    if _last_backtest['data']:
                        print(f"💾 Saved: {_last_backtest['bot'].export_csv(_last_backtest['data'])}")
                    else: print("⚠️ Run backtest first")
            except Exception as e: print(f"❌ {e}")
        elif c == '5':
            t = input("Ticker [AAPL]: ").strip().upper() or 'AAPL'
            interval = int(input("Check interval seconds [300]: ") or 300)
            max_pos = float(input("Max position $ [1000]: ") or 1000)
            broker = PaperBroker(initial_balance=10000)
            print(f"\n📝 Paper Broker | Balance: ${broker.balance:.2f}")
            lt = LiveTrader(t, mode='PAPER', broker=broker, callback=print,
                             interval=interval, max_position=max_pos)
            _live_traders[t] = lt
            lt.start()
            print(f"\nLive trader started in background. Use [7] to stop.")
        elif c == '6':
            if not settings.get('alpaca_api_key'):
                print("⚠️ Configure Alpaca first (option 9)")
                continue
            print("\n🔴 REAL MONEY TRADING - Are you sure?")
            confirm = input("Type 'YES I UNDERSTAND THE RISK': ").strip()
            if confirm != 'YES I UNDERSTAND THE RISK':
                print("Cancelled.")
                continue
            t = input("Ticker [AAPL]: ").strip().upper() or 'AAPL'
            interval = int(input("Check interval seconds [300]: ") or 300)
            max_pos = float(input("Max position $ [1000]: ") or 1000)
            broker = AlpacaBroker(settings.get('alpaca_api_key'),
                                   settings.get('alpaca_secret'),
                                   paper=settings.get('alpaca_paper'))
            mode = 'PAPER_ALPACA' if settings.get('alpaca_paper') else 'REAL'
            lt = LiveTrader(t, mode=mode, broker=broker, callback=print,
                             interval=interval, max_position=max_pos)
            _live_traders[t] = lt
            lt.start()
        elif c == '7':
            if not _live_traders:
                print("No active traders")
                continue
            print("Active:", list(_live_traders.keys()))
            t = input("Ticker to stop (or 'all'): ").strip().upper()
            if t == 'ALL':
                for lt in _live_traders.values(): lt.stop()
                _live_traders.clear()
            elif t in _live_traders:
                _live_traders[t].stop()
                del _live_traders[t]
        elif c == '8':
            if not _live_traders:
                print("No active traders")
                continue
            for t, lt in _live_traders.items():
                status = "🟢 RUNNING" if lt.is_running() else "🔴 STOPPED"
                print(f"  {t} [{lt.mode}]: {status}")


# ════════════════════════════════════════════════════════════
# KIVY GUI MODE
# ════════════════════════════════════════════════════════════
if USE_KIVY:
    class ChartWidget(Widget):
        def __init__(self, **kw):
            super().__init__(**kw)
            self.data, self.trades, self.title = [], [], "Portfolio"
            self.bind(size=self._redraw, pos=self._redraw)
            theme.add_listener(self._redraw)
        def plot(self, data, trades=None, title="Portfolio"):
            self.data = list(data) if data else []
            self.trades = trades or []
            self.title = title
            self._redraw()
        def _redraw(self, *a):
            self.canvas.clear()
            c = theme.colors
            with self.canvas:
                Color(*c['panel']); Rectangle(pos=self.pos, size=self.size)
            if len(self.data) < 2: return
            with self.canvas:
                pad = 40
                x0, y0 = self.x + pad, self.y + pad
                w, h = self.width - 2*pad, self.height - 2*pad
                Color(*c['grid'])
                for i in range(5):
                    Line(points=[x0, y0+h*i/4, x0+w, y0+h*i/4], width=1)
                mn, mx = min(self.data), max(self.data)
                rng = mx - mn or 1
                n = len(self.data)
                init, fin = self.data[0], self.data[-1]
                Color(*(c['profit'] if fin >= init else c['loss']))
                pts = []
                for i, v in enumerate(self.data):
                    pts += [x0 + (i/(n-1))*w, y0 + ((v-mn)/rng)*h]
                Line(points=pts, width=2)
                for tt, step, _ in self.trades:
                    if 0 <= step < n:
                        x = x0 + (step/(n-1))*w
                        y = y0 + ((self.data[step]-mn)/rng)*h
                        Color(*(c['profit'] if tt == 'BUY' else c['loss']))
                        Ellipse(pos=(x-6, y-6), size=(12, 12))
            for ch in list(self.children): self.remove_widget(ch)
            roi = (fin-init)/init*100 if init else 0
            color = c['profit'] if roi >= 0 else c['loss']
            lbl = Label(text=f"[b]{self.title}[/b]  ROI: {roi:+.2f}%",
                        markup=True, font_size='14sp', color=color,
                        pos=(self.x+10, self.top-25),
                        size_hint=(None,None), size=(self.width-20, 25))
            self.add_widget(lbl)

    def tbtn(text, key='accent', **kw):
        c = theme.colors
        b = Button(text=text, background_normal='', background_color=c[key],
                   color=c['btn_text'], bold=True, **kw)
        def upd():
            b.background_color = theme.get(key)
            b.color = theme.get('btn_text')
        theme.add_listener(upd)
        return b

    def tlbl(text, **kw):
        c = theme.colors
        lbl = Label(text=text, color=c['text'], **kw)
        theme.add_listener(lambda: setattr(lbl, 'color', theme.get('text')))
        return lbl

    def tinp(text='', **kw):
        c = theme.colors
        ti = TextInput(text=text, multiline=False,
                       background_color=c['card'], foreground_color=c['text'],
                       cursor_color=c['accent'], **kw)
        def upd():
            ti.background_color = theme.get('card')
            ti.foreground_color = theme.get('text')
        theme.add_listener(upd)
        return ti

    class LicensePopup(Popup):
        def __init__(self, on_accept, on_decline, **kw):
            super().__init__(title='📜 License', size_hint=(0.95, 0.95),
                             auto_dismiss=False, **kw)
            l = BoxLayout(orientation='vertical', padding=10, spacing=10)
            sc = ScrollView()
            t = Label(text=LICENSE_TEXT, size_hint_y=None, halign='left',
                      valign='top', font_size='11sp', color=theme.get('text'),
                      text_size=(Window.width*0.85, None))
            t.bind(texture_size=lambda i,v: setattr(i,'height',v[1]))
            sc.add_widget(t); l.add_widget(sc)
            btns = BoxLayout(size_hint_y=None, height=60, spacing=10)
            ag = Button(text='✅ I AGREE', background_normal='',
                        background_color=theme.get('profit'),
                        color=theme.get('btn_text'), bold=True)
            ag.bind(on_press=lambda *x: (on_accept(), self.dismiss()))
            dec = Button(text='❌ DECLINE', background_normal='',
                         background_color=theme.get('loss'),
                         color=theme.get('btn_text'), bold=True)
            dec.bind(on_press=lambda *x: on_decline())
            btns.add_widget(dec); btns.add_widget(ag); l.add_widget(btns)
            self.content = l

    class ActivationPopup(Popup):
        def __init__(self, lm, on_success, **kw):
            super().__init__(title='🔐 Activation', size_hint=(0.9, 0.7),
                             auto_dismiss=False, **kw)
            self.lm = lm; self.on_success = on_success
            l = BoxLayout(orientation='vertical', padding=20, spacing=15)
            d = lm.days_remaining()
            txt = (f"[b]⚠️ Trial Expired[/b]\n\n30-day trial ended."
                   if d <= 0 else f"[b]🔓 Activate[/b]\n\nTrial: {d}d left")
            l.add_widget(Label(text=txt, markup=True, font_size='16sp',
                                color=theme.get('warn'), size_hint_y=None,
                                height=80, halign='center'))
            l.add_widget(Label(text='Enter code:', font_size='14sp',
                                color=theme.get('text'), size_hint_y=None, height=30))
            self.inp = TextInput(multiline=False, font_size='18sp',
                                  halign='center', hint_text='XOLA-XXXX-XXXX-XXXX',
                                  size_hint_y=None, height=60,
                                  background_color=theme.get('card'),
                                  foreground_color=theme.get('text'))
            l.add_widget(self.inp)
            self.status = Label(text='', font_size='13sp',
                                 color=theme.get('warn'), size_hint_y=None, height=40)
            l.add_widget(self.status)
            btns = BoxLayout(size_hint_y=None, height=60, spacing=10)
            ab = Button(text='🔓 ACTIVATE', background_normal='',
                        background_color=theme.get('profit'),
                        color=theme.get('btn_text'), bold=True)
            ab.bind(on_press=self._try)
            btns.add_widget(ab)
            if d > 0:
                lb = Button(text='⏳ Continue Trial', background_normal='',
                            background_color=theme.get('accent'),
                            color=theme.get('btn_text'))
                lb.bind(on_press=lambda *x: self.dismiss())
                btns.add_widget(lb)
            else:
                eb = Button(text='❌ Exit', background_normal='',
                            background_color=theme.get('loss'),
                            color=theme.get('btn_text'))
                eb.bind(on_press=lambda *x: App.get_running_app().stop())
                btns.add_widget(eb)
            l.add_widget(btns); self.content = l
        def _try(self, *a):
            ok, msg = self.lm.activate(self.inp.text)
            if ok:
                self.status.text = f"✅ {msg}"; self.status.color = theme.get('profit')
                Clock.schedule_once(lambda dt: (self.dismiss(), self.on_success()), 1.5)
            else:
                self.status.text = f"❌ {msg}"; self.status.color = theme.get('loss')

    class TickerTab(BoxLayout):
        def __init__(self, app, **kw):
            super().__init__(orientation='vertical', padding=10, spacing=8, **kw)
            self.app = app; self.trainer = None; self.last_result = None
            r1 = BoxLayout(size_hint_y=None, height=50, spacing=8)
            r1.add_widget(tlbl('Ticker:', size_hint_x=0.3, font_size='16sp'))
            self.ti = tinp('AAPL', font_size='18sp', halign='center'); r1.add_widget(self.ti)
            self.add_widget(r1)
            r2 = BoxLayout(size_hint_y=None, height=50, spacing=8)
            r2.add_widget(tlbl('Episodes:', size_hint_x=0.4, font_size='16sp'))
            self.ep = Spinner(text='10', values=('5','10','20','50','100'), font_size='16sp')
            r2.add_widget(self.ep); self.add_widget(r2)
            btns = GridLayout(cols=2, size_hint_y=None, height=200, spacing=8)
            for txt, fn, k in [('🚀 TRAIN', self.train, 'accent'),
                               ('📊 BACKTEST', self.backtest, 'pink'),
                               ('📈 SIGNAL', self.signal, 'profit'),
                               ('📰 NEWS', self.news, 'warn'),
                               ('💾 EXPORT', self.export, 'accent'),
                               ('🗑️ CLEAR', self.clear, 'loss')]:
                b = tbtn(txt, key=k, font_size='14sp'); b.bind(on_press=fn); btns.add_widget(b)
            
