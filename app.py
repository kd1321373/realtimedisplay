import speech_recognition as sr  # type: ignore
from flask import Flask, render_template, jsonify  # type: ignore
from flask_socketio import SocketIO  # type: ignore
import threading
import os
import signal

app = Flask(__name__)
socketio = SocketIO(app)
recognizer = sr.Recognizer()

is_running = True  # 音声認識の実行フラグ

def process_text(text):
    """取得したテキストを単語リストに変換"""
    words = text.split()  # スペースで分割
    return words

def capture_audio():
    """マイクから定期的に音声を取得してテキストに変換する関数"""
    global is_running
    with sr.Microphone() as source:
        while is_running:  # 実行フラグがTrueの間、音声認識を実行
            try:
                print("Listening for 5 seconds...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                text = recognizer.recognize_google(audio, language="ja-JP")
                print(f"Recognized: {text}")
                words = process_text(text)
                print(f"Processed Words: {words}")
                socketio.emit('new_text', words)  # 単語リストを送信
            except sr.UnknownValueError:
                print("Could not understand audio.")
            except sr.RequestError as e:
                print(f"Error: {e}")
                break

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stop', methods=['POST'])
def stop_audio():
    """音声認識スレッドを停止し、サーバー自体を強制終了するエンドポイント"""
    global is_running
    is_running = False
    print("Stopping audio capture and shutting down server...")
    
    # 現在のプロセスに SIGINT を送信して終了
    os.kill(os.getpid(), signal.SIGINT)

if __name__ == '__main__':
    # スレッドを1つだけ作成
    audio_thread = threading.Thread(target=capture_audio)
    audio_thread.daemon = True  # サーバーが終了するとスレッドも終了
    audio_thread.start()

    # サーバーを開始
    socketio.run(app, debug=True)
