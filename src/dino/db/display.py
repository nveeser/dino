from sqlalchemy.orm import object_session

import sqlalchemy.orm as sa_orm
import sqlalchemy.types as sa_types
import sqlalchemy.orm.properties as sa_props

from dino.config import class_logger  
import element

class DisplayProcessor(object):
    ''' Processor to transform an instance to some form of output for display '''

    def show(self, instance):
        ''' Transform the specified instance into 
        - a string 
        - (list, tuple, generator) of strings 
        to be used to display the contents of the instance
        
        '''        
        raise NotImplemented()

class EntityDisplayProcessor(DisplayProcessor):
    
    def show(self, entity):
        return "\n".join(self._get_info(entity))
            
    def _get_info(self, entity):            
        yield ""
        yield "Description:"
        if hasattr(entity, '__doc__') and entity.__doc__ is not None:
            yield  entity.__doc__
        else:             
            yield "This is the %s Entity\n" % entity.__name__
        yield ""
        
        yield  "Element: " + str( issubclass(entity, element.Element))
        revisioned = issubclass(entity, element.Element) and entity.has_revision_entity()
        yield "Revisioned: "  + str(revisioned)
        yield "Resource: " + str( issubclass(entity, element.ResourceElement))        
        
        yield ""
        
        props = list(entity.mapper.iterate_properties)
        col_props = set([ p for p in props if isinstance(p, sa_props.ColumnProperty) ])
        rel_props = set([ p for p in props if isinstance(p, sa_props.RelationProperty) ])
        
        relation_names = [ p.key for p in rel_props ]
        rel_id_props = set([ p for p in col_props 
                                if p.key.endswith("_id") and p.key[:-3] in relation_names ])

        readonly_props = set([ p for p in props
                if p.key in ('instance_name','id', 'revision', 'changeset') ])   

        yield "System Properties:"
        for prop in col_props & readonly_props:                    
            yield " " + prop.key + ":  " +  self._get_column_info(prop)
        for prop in rel_props & readonly_props:
            yield " " + prop.key + " -> " +  self._get_relation_info(prop)
                
            
        yield ""
    
        yield "Columns:" 
        for col_prop in col_props - rel_id_props - readonly_props:    
            #print type(col_prop.columns[0].type)            
            yield " " + col_prop.key + ":  " +  self._get_column_info(col_prop)
            
        yield ""
        
        yield "Relationships:"
        for rel_prop in rel_props - readonly_props:
            print " " + rel_prop.key + " -> " +  self._get_relation_info(rel_prop)
         
        yield ""
    
        if issubclass(entity, element.ResourceElement):
            yield "Resource Format:"
            self._print_doc(entity.create_resource.__doc__, indent="   ")
    
    def _get_column_info(self, col_prop):
        col_type = col_prop.columns[0].type
        if isinstance(col_type, sa_types.String):
            return "%s(%s)" % (col_type.__class__.__name__, col_type.length)
        else:
            return str(col_type)
            
    def _get_relation_info(self, rel_prop):
        if isinstance(rel_prop.argument, sa_orm.Mapper):            
            target_cls = rel_prop.argument.class_
        else:
            target_cls = rel_prop.argument
        
        if rel_prop.uselist:
            return "[ " + target_cls.__name__ + ", ... ]"
        else:
            return target_cls.__name__

    def _print_doc(self, docstr, indent=""):
        ''' Print out the docstring, removing any whitespace begining or ending the line
            Add specified indentation.
        '''
        for line in docstr.split('\n'):
            line = line.strip()
            print indent + line
            

class FormDisplayProcessor(DisplayProcessor):
    ''' Default DisplayProcessor using an MultiElementFormProcessor '''
    
    def show(self, instance):
        from dino.db.element_form import MultiElementFormProcessor
        session = object_session(instance)
        return MultiElementFormProcessor(session, show_headers=True).to_form(instance)
        
class_logger(FormDisplayProcessor)



class RackDisplayProcessor(DisplayProcessor):
    
    def show(self, rack):
        from dino.db.schema import Rack
        assert isinstance(rack, Rack)
        
        rack_list = self.RackElementList(self, rack)
                
        rowlist = list( rack_list.row_list() )        
        rowlist.reverse()
        
        return "\n".join([ "%02d  %s" % (i, r) for i,r in rowlist ])
        

    class RackElement(object):
        def __init__(self, start_loc, label, size):
            self.start_loc = start_loc
            self.label = label
            self.size = size
    
    
        TOP    = "/----------------------------------------\\"
        MIDDLE = "|                                        |"
        BOTTOM_MUTLI = "\\%s/"
        BOTTOM_SINGLE = "<%s>"
        
        def units(self):
            s = [ self.MIDDLE for i in range(0, self.size-2) ]
            
            if self.size > 1:                
                s.append(self.TOP)
                s.insert(0, self.BOTTOM_MUTLI % self.bottom_label())
            else:
                s.insert(0, self.BOTTOM_SINGLE % self.bottom_label())
            return s
    
        def bottom_label(self):
            return self.label[:].center(40, '-')

            
    class EmptyElement(RackElement):
        TOP    = ""
        MIDDLE = ""
        BOTTOM_MUTLI = "%s"
        BOTTOM_SINGLE = "%s"
        
        def __init__(self, start_loc):
            RackDisplayProcessor.RackElement.__init__(self, start_loc, "Empty", 1)
            
        def bottom_label(self):
            return self.label[:].center(40, ' ')  
            
                
    class RackElementList(list):
        def __init__(self, proc, rack):
            device_dict = dict( [ (dev.rackpos, dev) for dev in rack.devices ])
            
            row_id = 1
            while row_id <= rack.size:
                                
                if device_dict.has_key(row_id):                
                    dev = device_dict[row_id] 
                    if dev.host:
                        label = str(dev.host)
                    else:
                        label = str(dev)
                    
                    proc.log.finest("Row: %d [%s]" % (row_id, label))
                    self.append(proc.RackElement(row_id, label, dev.chassis.racksize))                
    
                    row_id += dev.chassis.racksize        
                                        
                else:
                    if len(self) > 0 and isinstance(self[-1], proc.EmptyElement):
                        self[-1].size += 1
                    else:
                        self.append(proc.EmptyElement(row_id))
    
                    proc.log.finest("Row: %d [<Empty>]" % row_id)
                    
                    row_id += 1
    
            
        def _row_iterator(self):
            for element in self:
                for row in element.units():
                    yield row
    
        def row_list(self):
            for i, row in enumerate(self._row_iterator()):
                yield (i+1, row)


class_logger(RackDisplayProcessor)            


class SubnetDisplayProcessor(DisplayProcessor):
    
    ''' form show example
    def show(self, subnet):
        from dino.db.schema import Subnet
        assert isinstance(subnet, Subnet)
        
        #ip_list = self.RackElementList(self,subnet) 
                
        #return [ "%02d  %s" % (i, r) for i,r in ip_list ]
    ''' 


    def show(self, instance):
        from dino.db.element_form import ElementFormProcessor
        session = object_session(instance)
        processor = ElementFormProcessor.create(session, show_headers=True)                            
        return processor.to_form(instance)

              
class_logger(SubnetDisplayProcessor)            

