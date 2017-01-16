import zmq
import optparse


def main():
    parser = optparse.OptionParser()
    parser.add_option("-s", "--subscribe", dest="subscriber", help="Subscriber endpoint", action="append")
    parser.add_option("-p", "--publish", dest="publisher", help="Publisher endpoint", action="append")

    options, args = parser.parse_args()
    if options.subscriber is None or options.publisher is None:
        parser.print_help()
        exit(2)

    ctx = zmq.Context.instance()
    xpub = ctx.socket(zmq.XPUB)
    xsub = ctx.socket(zmq.XSUB)
    for ep in options.publisher:
        xpub.bind(ep)
    for ep in options.subscriber:
        xsub.bind(ep)
    zmq.proxy(xpub, xsub)

if __name__ == "__main__":
    main()
