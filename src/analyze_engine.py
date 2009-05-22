''' Parse SA Engine logging output to make better sense of it...''' 
import sys
import os
import re



class Analyze(object):
    
    def __init__(self, filename):
        self.filename = filename

        self.sql = None
        
    REGEX_SET = [ 
        re.compile("\s*(select).*from\s*(\S*).*", re.I),
        re.compile("\s*(update)\s*(\S*)\s*.*", re.I),
        re.compile("\s*(insert)\s*(\S*)\s*.*", re.I),
        re.compile("\s*(delete)\s*(\S*)\s*.*", re.I)
    ]
    
    def handle_dino(self, statement):
        print "<DINO>", statement

    def handle_sql(self, sql, params):
        
        value = self.match_sql(sql)
        if value:
            print "   <SQL>", value, params
        else:
            print "   <TEXT>", sql[0:50]

    
    def match_sql(self, sql):
        for regex in self.REGEX_SET:
            m = regex.search(self.sql)
            if m:
                return m.groups()
        return None
        
    def process(self):
        f = open(self.filename)

        for line in f.readlines():
            line = line.strip()            
            #print "--", line[:80]            
            m = re.match('\[dino.*\]:(.*)', line)
            if m:
                self.handle_dino(m.group(1))
                continue
            
            m = re.match('\[sqlalchemy\.engine\.base\.Engine\..*\]:\s*(\[.*\])', line)
            if m:
                #print "MATCH: params"
                assert self.sql is not None
                self.handle_sql( self.sql, m.group(1) )
                self.sql = None   
                continue
                
            m = re.match('\[sqlalchemy\.engine\.base\.Engine\..*\]:\s*([^[]?.*)', line)
            if m:        
                #print "MATCH: sql"
                self.sql = m.group(1)
                continue
                
            if self.sql is not None:
                self.sql += " " + line


a = Analyze(sys.argv[1])
a.process()
        