import math
import logging

logger = logging.getLogger(__name__)

def parse_ogg_pages(data: bytes) -> list:
    """
    Parses raw Ogg bytes and returns a list of dictionaries, 
    each containing header information and page bytes.
    """
    pages = []
    offset = 0
    data_len = len(data)
    
    while offset < data_len:
        # Scan for the OggS magic number (capture pattern)
        if not data.startswith(b'OggS', offset):
            next_idx = data.find(b'OggS', offset)
            if next_idx == -1:
                break
            offset = next_idx
        
        if offset + 27 > data_len:
            break
            
        header_type = data[offset + 5]
        granule_pos = int.from_bytes(data[offset + 6:offset + 14], byteorder='little', signed=False)
        serial_num = int.from_bytes(data[offset + 14:offset + 18], byteorder='little')
        seq_num = int.from_bytes(data[offset + 18:offset + 22], byteorder='little')
        checksum = int.from_bytes(data[offset + 22:offset + 26], byteorder='little')
        num_segments = data[offset + 26]
        
        if offset + 27 + num_segments > data_len:
            break
            
        segment_table = data[offset + 27 : offset + 27 + num_segments]
        data_size = sum(segment_table)
        
        total_page_size = 27 + num_segments + data_size
        if offset + total_page_size > data_len:
            break
            
        page_bytes = data[offset : offset + total_page_size]
        
        pages.append({
            'header_type': header_type,
            'granule_pos': granule_pos,
            'serial_num': serial_num,
            'seq_num': seq_num,
            'checksum': checksum,
            'data': page_bytes
        })
        
        offset += total_page_size
        
    return pages

def split_ogg(data: bytes, segment_duration_sec: float = 60.0) -> list:
    """
    Splits an Ogg Opus stream into smaller, playable Ogg byte segments.
    Uses granule position (Opus sample rate of 48000Hz) to estimate duration.
    """
    pages = parse_ogg_pages(data)
    if len(pages) < 3:
        return [data]
        
    # The first 2 pages are usually container identification (OpusID & OpusTags)
    headers = pages[0]['data'] + pages[1]['data']
    audio_pages = pages[2:]
    
    # Estimate total duration using granule position of the last audio page
    # Granule position for Opus in Ogg is measured in PCM samples at 48 kHz.
    total_samples = 0
    for p in reversed(audio_pages):
        if p['granule_pos'] > 0:
            total_samples = p['granule_pos']
            break
            
    # Calculate duration
    duration = total_samples / 48000.0 if total_samples > 0 else 0.0
    
    # If duration is 0, estimate using file size (assuming standard 24kbps Ogg Opus)
    if duration == 0:
        duration = len(data) / (24 * 1024 / 8)
        
    logger.info(f"Ogg stream detected: {len(pages)} pages, estimated duration: {duration:.2f} seconds")
    
    # Only split if it exceeds 3 minutes (180 seconds) or if explicit chunking is needed
    if duration <= 180.0:
        logger.info("Audio duration <= 3 minutes. Skipping splitting.")
        return [data]
        
    chunk_count = math.ceil(duration / segment_duration_sec)
    logger.info(f"Splitting audio into {chunk_count} segments of ~{segment_duration_sec}s")
    
    pages_per_chunk = math.ceil(len(audio_pages) / chunk_count)
    chunks = []
    
    for i in range(chunk_count):
        start_idx = i * pages_per_chunk
        end_idx = min(start_idx + pages_per_chunk, len(audio_pages))
        chunk_audio_pages = audio_pages[start_idx:end_idx]
        
        # Combine the common headers with the specific audio pages for this chunk
        chunk_data = headers + b"".join(p['data'] for p in chunk_audio_pages)
        chunks.append(chunk_data)
        
    return chunks
