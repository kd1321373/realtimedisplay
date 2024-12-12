import os
import sounddevice as sd  # type: ignore
import numpy as np  # type: ignore
import queue
import time
import speech_recognition as sr  # type: ignore
from flask import Flask, render_template, jsonify  # type: ignore
from flask_socketio import SocketIO  # type: ignore
import threading

# 設定
SAMPLERATE = 44100  # サンプリングレート
BUFFER_SIZE = 2048  # バッファサイズ（チャンクサイズ）
OUTPUT_INTERVAL = 10  # 出力間隔（秒）

app = Flask(__name__)
socketio = SocketIO(app)
recognizer = sr.Recognizer()

# データ用キュー
q = queue.Queue()

# 音声認識の状態を管理するフラグ
recognition_failed = False

# 5秒ごとに「音声を認識できませんでした。」を表示
def print_error_message():
    global recognition_failed

# コールバック関数
def audio_callback(indata, frames, time, status):
    if status:
        print(f"Error: {status}")
    q.put(indata.copy())

# 音声認識処理
def recognize_audio():
    global recognition_failed
    try:
        # PCM データを WAV フォーマットに変換
        audio_data = []
        while not q.empty():
            audio_data.append(q.get())

        if len(audio_data) > 0:
            audio_data = np.concatenate(audio_data, axis=0)
            # PCM 16bit に変換
            audio_data = (audio_data * 32767).astype(np.int16)
            wav_data = sr.AudioData(audio_data.tobytes(), SAMPLERATE, 2)

            # 音声認識
            text = recognizer.recognize_google(wav_data, language="ja-JP")
            print(f"認識結果: {text}")
            socketio.emit('new_text', text.split())  # 単語単位でクライアントに送信
            recognition_failed = False  # 認識が成功したので失敗フラグをリセット

    except sr.UnknownValueError:
        recognition_failed = True
        #print("音声を認識できませんでした。")
    except sr.RequestError as e:
        recognition_failed = True
        print(f"APIエラー: {e}")

# 音声ストリーミング開始
def start_audio_stream():
    stream = sd.InputStream(
        samplerate=SAMPLERATE,
        blocksize=BUFFER_SIZE,
        channels=1,
        callback=audio_callback
    )

    print("Recording...")
    stream.start()

    # 音声認識処理をバックグラウンドで開始
    while True:
        recognize_audio()

# Flaskルート
@app.route('/')
def index():
    return render_template('index.html')

# 停止用のルートを追加
@app.route('/stop', methods=['POST'])
def stop_server():
    """サーバーを停止させる"""
    print("サーバー停止要求を受け取りました...")
    os._exit(0)  # サーバーを終了

# サーバー起動
if __name__ == '__main__':
    # エラーメッセージを5秒ごとに表示するスレッドを開始
    error_thread = threading.Thread(target=print_error_message)
    error_thread.daemon = True  # サーバー終了時にスレッドも終了
    error_thread.start()

    # 音声ストリーミングを別スレッドで実行
    audio_thread = threading.Thread(target=start_audio_stream)
    audio_thread.daemon = True
    audio_thread.start()

    # Flaskサーバーを開始
    socketio.run(app, debug=True)