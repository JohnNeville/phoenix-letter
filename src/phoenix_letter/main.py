import random
import sys
from argparse import ArgumentParser
from time import sleep

import boto3


def parse_arguments(args):
    parser = ArgumentParser()
    parser.add_argument("--src", dest="source",
                        required=True,
                        help="Source SQS Queue Name",
                        metavar="SOURCE_QUEUE")

    parser.add_argument("--dst", dest="destination",
                        required=True,
                        help="Destination SQS Queue Name",
                        metavar="DESTINATION_QUEUE")

    parser.add_argument("--access-key", dest="access_key",
                        required=True,
                        help="AWS Access Key",
                        metavar="AWS_USER_ACCESS_KEY")

    parser.add_argument("--secret-key", dest="secret_key",
                        required=True,
                        help="AWS Secret Key",
                        metavar="AWS_USER_SECRET_KEY")

    parser.add_argument("--region", dest="region", default="us-east-1",
                        required=True,
                        help="AWS Region",
                        metavar="REGION")

    parser.add_argument("--empty-receive", dest="max_empty_receives_count", default=10,
                        help="Max number of empty receives before giving up",
                        metavar="EMPTY_RECEIVE")

    parser.add_argument("--max-messages", dest="max_messages", default=-1,
                        help="Max number of messages to receive before stopping",
                        metavar="MAX_MESSAGES")

    parser.add_argument("--messages-per-loop", dest="messages_per_loop", default=10,
                        help="Number of messages per loop",
                        metavar="MESSAGES_PER_LOOP")

    return parser.parse_args(args)


def main(args=None):
    args = parse_arguments(args)

    sqs_client = boto3.client("sqs", region_name=args.region,
                              aws_access_key_id=args.access_key,
                              aws_secret_access_key=args.secret_key)

    print("Getting Queue URLs")

    source_queue = sqs_client.get_queue_url(QueueName=args.source)
    source_queue_url = source_queue['QueueUrl']

    destination_queue = sqs_client.get_queue_url(QueueName=args.destination)
    destination_queue_url = destination_queue['QueueUrl']

    number_of_empty_receives = 0
    number_receives = 0

    # Prevent loading more messages than the max
    if(args.max_messages != -1 and args.max_messages < args.messages_per_loop):
        args.messages_per_loop = args.max_messages

    print("Getting the first {} messages".format(args.max_messages))
    
    while number_of_empty_receives <= int(args.max_empty_receives_count) and (number_receives < int(args.max_messages) or int(args.max_messages) == -1):
        print("Receiving message...")
        received_response = sqs_client.receive_message(QueueUrl=source_queue_url, MessageAttributeNames=["All"],
                                                        AttributeNames=['All'],
                                                        MaxNumberOfMessages=int(args.messages_per_loop))

        if ("Messages" not in received_response) or (len(received_response['Messages']) == 0):
            print("Queue did not returned messages")

            number_of_empty_receives += 1
            sleep_time = random.randint(500, 2000) / 1000

            print("Sleeping for {} seconds".format(sleep_time))
            sleep(sleep_time)

            continue
        print("Received {} messages".format(len(received_response['Messages'])))

        for message in received_response['Messages']:
            if(number_receives <= int(args.max_messages) or int(args.max_messages) == -1):
                number_receives += 1
                print("Sending message to '{}'".format(args.destination))

                send_response = sqs_client.send_message(QueueUrl=destination_queue_url,
                                                        MessageBody=message['Body'],
                                                        MessageAttributes=message['MessageAttributes'])

                print("Deleting message from '{}'".format(args.source))
                sqs_client.delete_message(QueueUrl=source_queue_url,ReceiptHandle=message['ReceiptHandle'])
    print("Giving up after {} empty receives from the source queue.".format(number_of_empty_receives))

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
