// ── Socket.IO 连接 ─────────────────────────────────────
const socket = io();

// ── 状态变量 ───────────────────────────────────────────
let mySid = null;
let myNickname = '';
let myWord = '';
let countdownInterval = null;

// ── DOM 元素 ───────────────────────────────────────────
const views = {
    lobby: document.getElementById('view-lobby'),
    waiting: document.getElementById('view-waiting'),
    word: document.getElementById('view-word'),
    voting: document.getElementById('view-voting'),
    result: document.getElementById('view-result'),
    ended: document.getElementById('view-ended'),
};

const nicknameInput = document.getElementById('nickname-input');
const btnJoin = document.getElementById('btn-join');
const btnStart = document.getElementById('btn-start');
const btnVote = document.getElementById('btn-vote');
const btnEnd = document.getElementById('btn-end');
const btnBack = document.getElementById('btn-back');
const playerListEl = document.getElementById('player-list');
const wordPlayersEl = document.getElementById('word-players');
const voteListEl = document.getElementById('vote-list');
const myWordEl = document.getElementById('my-word');
const roundNumEl = document.getElementById('round-num');
const countdownEl = document.getElementById('countdown-timer');
const voteStatus = document.getElementById('vote-status');
const resultContent = document.getElementById('result-content');
const toastEl = document.getElementById('toast');

// ── 视图切换 ───────────────────────────────────────────
function showView(name) {
    Object.values(views).forEach(v => v.classList.remove('active'));
    if (views[name]) views[name].classList.add('active');
}

// ── Toast 提示 ─────────────────────────────────────────
function showToast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    setTimeout(() => toastEl.classList.remove('show'), 3000);
}

// ── 渲染玩家列表 ───────────────────────────────────────
function renderPlayerList(container, players, options = {}) {
    container.innerHTML = '';
    players.forEach(p => {
        const tag = document.createElement('div');
        tag.className = 'player-tag';

        if (p.eliminated) tag.classList.add('eliminated');

        let label = p.nickname;
        if (p.sid === mySid) label += ' (我)';

        tag.textContent = label;

        if (options.votable && p.sid !== mySid && !p.eliminated) {
            tag.classList.add('vote-option');
            tag.addEventListener('click', () => handleVote(p.sid, tag));
        }

        container.appendChild(tag);
    });
}

// ── 事件绑定 ───────────────────────────────────────────

btnJoin.addEventListener('click', () => {
    const nick = nicknameInput.value.trim();
    if (!nick) {
        showToast('请输入昵称！');
        return;
    }
    socket.emit('join_game', { nickname: nick });
});

nicknameInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') btnJoin.click();
});

btnStart.addEventListener('click', () => {
    socket.emit('start_game');
});

btnVote.addEventListener('click', () => {
    socket.emit('start_voting');
});

btnEnd.addEventListener('click', () => {
    socket.emit('end_game');
});

btnBack.addEventListener('click', () => {
    location.reload();
});

// ── 投票处理 ───────────────────────────────────────────
let hasVoted = false;

function handleVote(targetSid, tagEl) {
    if (hasVoted) {
        showToast('你已经投过票了！');
        return;
    }
    socket.emit('vote', { target: targetSid });
    tagEl.classList.add('voted');
}

// ── 倒计时 ─────────────────────────────────────────────
function startCountdown(seconds) {
    clearInterval(countdownInterval);
    countdownEl.textContent = seconds;
    countdownInterval = setInterval(() => {
        seconds--;
        countdownEl.textContent = seconds;
        if (seconds <= 0) {
            clearInterval(countdownInterval);
        }
    }, 1000);
}

// ── Socket 事件监听 ────────────────────────────────────

socket.on('joined', (data) => {
    mySid = data.sid;
    myNickname = data.nickname;
});

socket.on('your_word', (data) => {
    myWord = data.word;
    myWordEl.textContent = data.word;
});

socket.on('vote_confirmed', (data) => {
    hasVoted = true;
    voteStatus.textContent = data.message;
});

socket.on('error', (data) => {
    showToast(data.message);
});

socket.on('game_ended', () => {
    showView('ended');
});

socket.on('game_update', (data) => {
    const state = data.state;

    if (state === 'lobby') {
        showView('waiting');
        renderPlayerList(playerListEl, data.players);

    } else if (state === 'waiting') {
        showView('waiting');
        renderPlayerList(playerListEl, data.players);

    } else if (state === 'word_assign') {
        showView('word');
        roundNumEl.textContent = data.round;
        renderPlayerList(wordPlayersEl, data.players);

    } else if (state === 'voting') {
        showView('voting');
        hasVoted = false;
        voteStatus.textContent = '';
        startCountdown(data.countdown || 15);
        renderPlayerList(voteListEl, data.players, { votable: true });

    } else if (state === 'result') {
        showView('result');
        if (data.tie) {
            resultContent.innerHTML = `<div class="tie">${data.message}</div>`;
        } else {
            const e = data.eliminated;
            resultContent.innerHTML = `
                <span class="eliminated-name">${e.nickname}</span> 已被投票出局<br>
                TA的身份是 <span class="role-text">${e.role_text}</span>
            `;
        }
    }
});
