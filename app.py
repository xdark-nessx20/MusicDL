from datetime import datetime
from flask import Flask, request, jsonify
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)
DOWNLOAD_FOLDER = 'music'
QUALITY_OPTIONS = {
    'normal': 'bestaudio[abr<=128]/best[abr<=128]', 
    'high': 'bestaudio[abr<=320]/best[abr<=320]',
    'maximum': 'bestaudio/best'
}

download_status = {}

is_music_file = lambda duration: duration <= 3600  # 1 hour limit
config_ydl = lambda quality: {
    'format': QUALITY_OPTIONS.get(quality, QUALITY_OPTIONS['normal']),
    'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
    'extractaudio': True,
    'audioformat': 'mp3',
    'audioquality': '0',
    'no_warnings': True,
    'ignoreerrors': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192' if quality == 'high' else '128'
    }]
}

#This function makes the downloads on background
def download_audio(download_id, url, quality='normal'):
    try:
        start_time = time.time()
        download_status[download_id] = {
            'status': 'downloading',
            'progress': 0,
            'message': 'Starting download...',
            'created_at': start_time,
            'started_at': start_time,
            'url': url,
            'quality': quality
        }

        ydl_opts = config_ydl(quality)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Update status to processing
            download_status[download_id].update({
                'status': 'processing',
                'message': 'Obteniendo información...'
            })
            
            # get video info
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Audio')
            artist = info.get('uploader', 'Unknown')
            duration = info.get('duration', 0)

            if not is_music_file(duration):
                download_status[download_id] = {
                    'status': 'error',
                    'message': 'Audio too long. Max 1 hour allowed.',
                }
                return
            
            # Update status to downloading
            download_status[download_id].update({
                'status': 'downloading',
                'title': title,
                'artist': artist,
                'duration': duration,
                'message': 'Downloading audio...'
            })

            ydl.download([url])

            completed_time = time.time()
            # Final update to success
            download_status[download_id] = {
                'status': 'completed',
                'title': title,
                'artist': artist,
                'duration': duration,
                'quality': quality,
                'message': 'Download completed successfully.',
                'created_at': download_status[download_id]['created_at'],  # Mantener tiempo original
                'started_at': download_status[download_id]['started_at'],
                'completed_at': completed_time,
                'download_time': f"{(completed_time - start_time):.1f}s",
                'url': url
            }

    except Exception as e:
        download_status[download_id] = {
            'success': False,
            'error': str(e),
            'message': 'An error occurred during download.',
            'created_at': download_status.get(download_id, {}).get('created_at', time.time()),
            'failed_at': time.time(),
            'url': url
        }
        return
    
@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', 'normal')

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided.'}), 400

    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    # Create a unique download ID
    download_id = str(uuid.uuid4())

    # Start the download in a separate thread
    thread = threading.Thread(
        target=download_audio, args=(download_id, url, quality)
    )
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Download started',
        'download_id': download_id,
        'status_url': f'/status/{download_id}'
    }), 202

#Verifies the status of one specific download
@app.route('/status/<download_id>', methods=['GET'])
def get_status(download_id):
    if download_id not in download_status:
        return jsonify({'error': 'Download ID not found'}), 404
    
    status = download_status[download_id].copy()

    # Convert timestamps to readable format
    if 'created_at' in status:
        status['created_date'] = datetime.fromtimestamp(status['created_at']).strftime('%Y-%m-%d %H:%M:%S')
    
    if 'completed_at' in status:
        status['completed_date'] = datetime.fromtimestamp(status['completed_at']).strftime('%Y-%m-%d %H:%M:%S')
        
    if 'failed_at' in status:
        status['failed_date'] = datetime.fromtimestamp(status['failed_at']).strftime('%Y-%m-%d %H:%M:%S')

    return jsonify(status)

#Verifies the status of all downloads
@app.route('/downloads', methods=['GET'])
def get_all_downloads():
    if not download_status:
        return jsonify({
            'total_downloads': 0,
            'downloads': [],
            'message': 'No downloads found'
        })
    
    # General stats
    total = len(download_status)
    completed = sum(1 for d in download_status.values() if d.get('status') == 'completed')
    downloading = sum(1 for d in download_status.values() if d.get('status') == 'downloading')
    errors = sum(1 for d in download_status.values() if d.get('status') == 'error')
    processing = sum(1 for d in download_status.values() if d.get('status') == 'processing')
    
    # List of downloads with details sorted by created_at
    downloads_list = []
    for download_id, status_info in download_status.items():
        # Convert timestamp to readable format
        created_timestamp = status_info.get('created_at', 0)
        created_date = datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        download_info = {
            'id': download_id,
            'status': status_info.get('status', 'unknown'),
            'message': status_info.get('message', ''),
            'created_at': created_timestamp,
            'created_date': created_date,  
        }
        
        # Add other fields if they exist
        if 'title' in status_info:
            download_info['title'] = status_info['title']
        if 'artist' in status_info:
            download_info['artist'] = status_info['artist']
        if 'duration' in status_info:
            download_info['duration'] = status_info['duration']
        if 'file_size' in status_info:
            download_info['file_size'] = status_info['file_size']
        if 'download_time' in status_info:
            download_info['download_time'] = status_info['download_time']
        if 'error' in status_info:
            download_info['error'] = status_info['error']
        if 'quality' in status_info:
            download_info['quality'] = status_info['quality']
            
        downloads_list.append(download_info)
    
    # Sort downloads by created_at descending
    downloads_list.sort(key=lambda x: x.get('created_at', 0), reverse=True)
    
    return jsonify({
        'total_downloads': total,
        'stats': {
            'completed': completed,
            'downloading': downloading,
            'processing': processing,
            'errors': errors
        },
        'downloads': downloads_list
    })

# Endpoint to clear downloads
@app.route('/downloads/clear', methods=['POST'])
def clear_downloads():
    data = request.json or {}
    clear_all = data.get('clear_all', False)
    
    if clear_all:
        # Clear all downloads
        cleared_count = len(download_status)
        download_status.clear()
        return jsonify({
            'success': True,
            'message': f'Cleared {cleared_count} downloads',
            'cleared_count': cleared_count
        })
    else:
        # Clear only completed and error downloads
        to_remove = []
        for download_id, status_info in download_status.items():
            status = status_info.get('status')
            if status in ['completed', 'error']:
                to_remove.append(download_id)
        
        for download_id in to_remove:
            del download_status[download_id]
        
        return jsonify({
            'success': True,
            'message': f'Cleared {len(to_remove)} completed/failed downloads',
            'cleared_count': len(to_remove),
            'remaining': len(download_status)
        })


@app.route('/test', methods=['GET'])
def test():
    return jsonify({'success': True, 'message': 'API is working.'}), 200