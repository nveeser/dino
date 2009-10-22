# -*- coding: utf-8 -*-
<%inherit file="/master.mako"/>

<table border="1">
    % for e in c.entity_set:
    <tr> <td> <a href=${h.url('elements', entity_name=str(e))}> ${e} </a></td> </tr>
    % endfor
</table>