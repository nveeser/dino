# -*- coding: utf-8 -*-
<%inherit file="/master.mako"/>

<script type="text/javascript" src="${h.url('/source/jquery.tree.js')}"></script>
<script type="text/javascript">	
    $(document).ready(function(){	
		$('.logtree').tree(
		{ 
			types :	{
				"default" : {
					clickable	: true,
					renameable	: false,
					deletable	: false,
					creatable	: false,
					draggable	: false,
					max_children	: -1,
					max_depth	: -1,
					valid_children	: "all",
			
					icon : {
						image : false,
						position : false
					}
				}
			}
		}
		);
	});
</script>

 <style type="text/css">
    .test { font-weight: bold; } 
 </style>


<%def name="log(name)">
	<li id="${name}" rel="logger-type"> 
		<% 
		import logging
		level = c.log_data[name][0].level
		levelName = logging._levelNames[level]
		%>
		<a href='#'>${name}</a> : ${levelName} 
	</li>
	<ul>

			
		% for handler in c.log_data[name][0].handlers:
		<li id="${handler}" rel='handler-type'> 
			<a href='#'> ${handler} </a> : ${logging.getLevelName(handler.level)}
		</li>
		% endfor
	</ul>
	<ul>	
		% for child_name in sorted(c.log_data[name][1]):
			${log(child_name)}
		% endfor
	</ul>	
</%def>

<a href="#" class='foo'> Link </a>

<div class='logtree'>
<ul>
	${log('root')}
</ul>
</div>