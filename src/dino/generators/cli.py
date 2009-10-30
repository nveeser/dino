class GeneratorCli(BaseDinoCli):

    def __init__(self, generator_cls):
        BaseDinoCli.__init__(self)
        self.generator_cls = generator_cls


    def setup_parser(self):
        parser = OptionParser()
        parser.allow_interspersed_args = False
        parser.add_option('-g', '--generate', action='store_true', default=False, help='generate only')
        parser.add_option('-c', '--compare', action='store_true', default=False, help='compare generated with active')
        parser.add_option('-a', '--activate', action='store_true', default=False, help='activate only')
        parser.add_option('-v', '--verbose', action='callback', callback=self.increase_verbose_cb)
        parser.add_option('-d', '--debug', action='store_true', default=False, help='debug output')
        parser.add_option('-x', '--xception-trace', action='store_true', dest='exception_trace', default=False)

        return parser


    def main(self, args):
        try:
            self.setup_base_logger("dino.generate")

            parser = self.setup_parser()
            (options, args) = parser.parse_args(args=args)

            db_config = self.create_db_config(options, section=section)
            generator_settings = self.get_config("generate")

            gen = self.generator_cls(db_config, generator_settings)
            gen.parse(args)

            if options.generate:
                gen.generate(args)

            if options.compare:
                gen.compare(args)

            if options.activate:
                gen.activate(args)

            if not options.generate and options.compare and options.activate:
                gen.generate(args)
                gen.activate(args)

        except GeneratorException, e:
            print "GeneratorException: ", e.args[0]
            if options.exception_trace: e.print_trace()
            sys.exit(-1)

        except sa_exc.DatabaseError, e:
            print "Database Error: %s.%s" % (e.__module__, e.__class__.__name__)
            if e.orig:
                print "\t (%s.%s)" % (e.orig.__module__, e.orig.__class__.__name__)
                args = [ str(a) for a in e.orig.args ]
                print "[ " + ", ".join(args) + " ]"

            print "STATEMENT:\n%s" % e.statement
            print "ARGS: %s" % str(e.params)

        except KeyboardInterrupt, e:
            print "Ctrl-C"
            sys.exit(1)
        except SystemExit, e:
            pass
        except Exception, e:
            print "Unknown Error: %s.%s" % (e.__module__, e.__class__.__name__)
            print e
            traceback.print_exc()
            sys.exit(1)

