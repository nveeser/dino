# -*- coding: utf-8 -*-
<%inherit file="/master.mako"/>

<table border="1">
	<thead>
	    <tr> 
	    	<th>Entity</th>
	    	<th>Element?</th>    	 
	    	<th>Revisioned?</th> 
	    </tr>
    </thead>
    <tbody>
	    % for (i, name, is_element, is_revisioned) in c.entity_data:
	    <tr class='${['odd','even'][i%2]}'> 
	    	<td> <a href='${h.url('elements', entity_name=name)}'> ${name} </a></td>
	    	<td> ${is_element} </td> 
	    	<td> ${is_revisioned} </td> 
	    </tr>
	    % endfor
    </tbody>
</table>