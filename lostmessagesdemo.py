"""
Import can log file into sqlite3 db.
"""
from can import LogReader, MessageSync, Logger

def main():
    reader = LogReader('data/test-log.log')
    in_nosync = MessageSync(reader, timestamps=False)
    logger = Logger('data/test-log.db')

    try:
        for msg in in_nosync:
            logger(msg)
    except KeyboardInterrupt:
        pass
    finally:
        reader.stop()
        logger.stop()

if __name__ == "__main__":
    main()
