# -*- coding: utf-8 -*-
<%inherit file="/master.mako"/>

<table border="1">
    % for e in c.elements:
    <tr> 
    	<td> <A href=${h.url('element', entity_name=e.entity_name, id=e.id)}> ${e}</A> </td> 
    </tr>
    % endfor
</table>