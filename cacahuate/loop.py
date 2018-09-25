from pika.exceptions import ConnectionClosed
import logging
import pika
import traceback

from .handler import Handler

LOGGER = logging.getLogger(__name__)


class Loop:

    def __init__(self, config: dict):
        self.config = config
        self.handler = Handler(config)

    def start(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=self.config['RABBIT_HOST'],
        ))
        channel = connection.channel()

        channel.queue_declare(
            queue=self.config['RABBIT_QUEUE'],
            durable=True,
        )
        LOGGER.info('Declared queue {}'.format(self.config['RABBIT_QUEUE']))

        channel.basic_consume(
            self.handler,
            queue=self.config['RABBIT_QUEUE'],
            consumer_tag=self.config['RABBIT_CONSUMER_TAG'],
            no_ack=self.config['RABBIT_NO_ACK'],
        )

        LOGGER.info('cacahuate started')

        retries = 0

        while cont:
            try:
                channel.start_consuming()
            except KeyboardInterrupt:
                LOGGER.info('cacahuate stopped')
                break
            except ConnectionClosed as e:
                if retries < self.config['RABBIT_RETRIES']:
                    retries += 1
                else:
                    LOGGER.warning('connection retry limit reached')
                    break
            except Exception as e:
                LOGGER.error(traceback.format_exc())
                break
