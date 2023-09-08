import logging

logger = logging.getLogger(__name__)

stream_handle = logging.StreamHandler()
stream_handle.setLevel(logging.INFO)
stream_handle_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
stream_handle.setFormatter(stream_handle_format)

logger.addHandler(stream_handle)
