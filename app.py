import json
import random
import math
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'who-is-undercover-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# ── 游戏全局状态 ──────────────────────────────────────
game = {
    'state': 'lobby',          # lobby / waiting / word_assign / voting / result
    'players': {},             # sid → {nickname, role, word}
    'undercover_word': '',
    'civilian_word': '',
    'round': 0,
    'votes': {},               # target_sid → count
    'voters': set(),           # 已投票的玩家 sid
    'eliminated': set(),       # 已出局的玩家 sid
    'timer': None,             # 定时器线程引用
}

# ── 加载词库 ──────────────────────────────────────────
def load_words():
    with open('words.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['word_pairs']

WORD_PAIRS = load_words()

# ── 辅助函数 ──────────────────────────────────────────

def get_player_list():
    """返回给前端的玩家列表（隐藏角色和词语）"""
    result = []
    for sid, p in game['players'].items():
        result.append({
            'sid': sid,
            'nickname': p['nickname'],
            'eliminated': sid in game['eliminated'],
        })
    return result

def get_player_list_with_roles():
    """返回带角色的玩家列表（结果展示用）"""
    result = []
    for sid, p in game['players'].items():
        result.append({
            'sid': sid,
            'nickname': p['nickname'],
            'role': p['role'],
            'eliminated': sid in game['eliminated'],
        })
    return result

def broadcast_state(extra=None):
    """向所有客户端广播当前游戏状态"""
    data = {
        'state': game['state'],
        'players': get_player_list(),
        'round': game['round'],
    }
    if extra:
        data.update(extra)
    socketio.emit('game_update', data)

def clear_timer():
    """清除当前定时器"""
    if game['timer']:
        game['timer'].cancel()
        game['timer'] = None

def start_voting():
    """启动投票阶段"""
    game['state'] = 'voting'
    game['votes'] = {}
    game['voters'] = set()
    game['round'] += 1
    broadcast_state({'countdown': 15})

    # 15 秒后自动结束投票
    game['timer'] = threading.Timer(15.0, finish_voting)
    game['timer'].start()

def finish_voting():
    """投票结束，计算结果"""
    game['timer'] = None
    game['state'] = 'result'

    # 统计投票结果
    if not game['votes']:
        # 没有人投票 → 平局
        result_data = {
            'tie': True,
            'message': '本轮无人投票，平局！',
            'vote_details': {},
        }
    else:
        max_votes = max(game['votes'].values())
        top_voted = [sid for sid, count in game['votes'].items() if count == max_votes]

        if len(top_voted) > 1:
            # 平局
            result_data = {
                'tie': True,
                'message': '本轮平局，无人出局！',
                'vote_details': game['votes'],
            }
        else:
            # 有人被投票出局
            eliminated_sid = top_voted[0]
            game['eliminated'].add(eliminated_sid)
            player = game['players'][eliminated_sid]
            role_text = '卧底' if player['role'] == 'undercover' else '平民'
            result_data = {
                'tie': False,
                'eliminated': {
                    'sid': eliminated_sid,
                    'nickname': player['nickname'],
                    'role': player['role'],
                    'role_text': role_text,
                },
                'message': f"{player['nickname']} 已被投票出局，TA的身份是{role_text}",
                'vote_details': game['votes'],
            }

    broadcast_state(result_data)

    # 5 秒后进入下一轮
    game['timer'] = threading.Timer(5.0, next_round)
    game['timer'].start()

def next_round():
    """进入下一轮"""
    game['timer'] = None
    game['state'] = 'word_assign'
    assign_words()

def assign_words():
    """分配词语"""
    active_players = [sid for sid in game['players'] if sid not in game['eliminated']]
    if len(active_players) < 2:
        # 人数不足，游戏结束
        game['state'] = 'lobby'
        reset_game()
        return

    # 随机选词对
    pair = random.choice(WORD_PAIRS)
    game['civilian_word'] = pair['civilian']
    game['undercover_word'] = pair['undercover']

    # 计算卧底人数 (15% ~ 33%)
    total = len(active_players)
    undercover_count = max(1, math.floor(total * random.uniform(0.15, 0.33)))

    # 随机选卧底
    undercover_sids = random.sample(active_players, undercover_count)

    for sid in active_players:
        if sid in undercover_sids:
            game['players'][sid]['role'] = 'undercover'
            game['players'][sid]['word'] = pair['undercover']
        else:
            game['players'][sid]['role'] = 'civilian'
            game['players'][sid]['word'] = pair['civilian']

    # 向每个玩家私发词语
    for sid in active_players:
        p = game['players'][sid]
        socketio.emit('your_word', {
            'word': p['word'],
            'role': p['role'],
        }, to=sid)

    broadcast_state({'round': game['round']})

def reset_game():
    """重置游戏状态"""
    game['state'] = 'lobby'
    game['players'] = {}
    game['undercover_word'] = ''
    game['civilian_word'] = ''
    game['round'] = 0
    game['votes'] = {}
    game['voters'] = set()
    game['eliminated'] = set()
    clear_timer()
    broadcast_state()


# ── 路由 ──────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ── WebSocket 事件 ────────────────────────────────────

@socketio.on('join_game')
def handle_join(data):
    """玩家加入游戏"""
    if game['state'] != 'lobby':
        emit('error', {'message': '游戏已开始，无法加入！'})
        return

    nickname = data.get('nickname', '').strip()
    if not nickname:
        emit('error', {'message': '请输入昵称！'})
        return

    # 检查昵称是否重复
    for p in game['players'].values():
        if p['nickname'] == nickname:
            emit('error', {'message': '该昵称已被使用！'})
            return

    from flask_socketio import request as sio_request
    sid = sio_request.sid
    game['players'][sid] = {
        'nickname': nickname,
        'role': None,
        'word': '',
    }

    emit('joined', {'sid': sid, 'nickname': nickname})
    broadcast_state()


@socketio.on('start_game')
def handle_start():
    """开始游戏"""
    from flask_socketio import request as sio_request
    sid = sio_request.sid

    if len(game['players']) < 4:
        emit('error', {'message': '至少需要 4 名玩家才能开始游戏！'})
        return

    if game['state'] != 'lobby':
        emit('error', {'message': '游戏已经在进行中！'})
        return

    # 标记状态为 waiting（锁定新玩家加入）
    game['state'] = 'waiting'
    broadcast_state()

    # 进入分词阶段
    game['state'] = 'word_assign'
    game['round'] = 1
    assign_words()


@socketio.on('start_voting')
def handle_start_voting():
    """主持人启动投票"""
    if game['state'] != 'word_assign':
        emit('error', {'message': '当前状态不能开始投票！'})
        return
    start_voting()


@socketio.on('vote')
def handle_vote(data):
    """玩家投票"""
    from flask_socketio import request as sio_request
    sid = sio_request.sid

    if game['state'] != 'voting':
        emit('error', {'message': '当前不是投票阶段！'})
        return

    if sid in game['voters']:
        emit('error', {'message': '你已经投过票了！'})
        return

    target = data.get('target', '')
    if not target or target not in game['players']:
        emit('error', {'message': '无效的投票目标！'})
        return

    if target == sid:
        emit('error', {'message': '不能给自己投票！'})
        return

    if target in game['eliminated']:
        emit('error', {'message': '该玩家已出局！'})
        return

    game['voters'].add(sid)
    game['votes'][target] = game['votes'].get(target, 0) + 1
    emit('vote_confirmed', {'message': '投票成功！'})


@socketio.on('end_game')
def handle_end_game():
    """结束游戏"""
    reset_game()
    socketio.emit('game_ended', {'message': '游戏已结束！'})


@socketio.on('disconnect')
def handle_disconnect():
    """玩家断开连接"""
    from flask_socketio import request as sio_request
    sid = sio_request.sid
    if sid in game['players']:
        del game['players'][sid]
        if game['state'] == 'lobby':
            broadcast_state()


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
