# -*- coding: utf-8 -*-
<%inherit file="/master.mako"/>
<%!
	import dino.db.element as element
%>

<table border="1">
	<thead>
    <tr> 
		<th> Name </th>
		<th> Value </th>
    </tr>
    </thead>
    <tbody>
    % for (i, (name, value)) in enumerate(c.element_data):
	    <tr class='${['odd','even'][i%2]}'>
	    	<td> ${name} </td>
    		% if isinstance(value, element.Element): 
    			<td> <A href=${h.url('element', entity_name=value.entity_name, id=value.id)}> ${value}</A> </td>
    		% elif isinstance(value, (list, set, dict)):
    			<td> ${len(value)} </td>
    		% else:    			
    			<td> ${value} </td>    			
    		% endif 
		</tr>
    % endfor
	</tbody>
</table>