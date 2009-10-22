# -*- coding: utf-8 -*-
<%inherit file="/master.mako"/>
<%!
	import dino.db.element as element
%>

<table border="1">
	<thead>
    <tr> 
		<th> id </th>
		<th> ElementName </th>
		% for name in c.element_prop_names:
			<th> ${name} </th>
		% endfor
    </tr>
    </thead>
    <tbody>
    % for (i, values) in enumerate(c.element_data):
    <tr class='${['odd','even'][i%2]}'>
    	% for value in values:
    		% if isinstance(value, element.Element): 
    			<td> <A href=${h.url('element', entity_name=value.entity_name, id=value.id)}> ${value}</A> </td>
    		% elif isinstance(value, (list, set, dict)):
    			<td> ${len(value)} </td>
    		% else:    			
    			<td> ${value} </td>    			
    		% endif 
		% endfor
	</tr>
    % endfor
	</tbody>
</table>