# -*- coding: utf-8 -*-
<%inherit file="/master.mako"/>

<table border="1">
	<thead>
    <tr> 
    	<th>Path</td>
    	<th>Name</td>    	 
    	<th>Conditions</td> 
    	<th>Defaults</td> 
    	<th>Hardcoded</td> 
    </tr>
    </thead>
     % for i,r in enumerate(c.routes):
    <tr class='${['odd','even'][i%2]}'> 
    	<td>${ r.routepath }</td>
    	<td>${ r.name or "" }</td>    	 
    	<td>${ r.conditions or ""}</td> 
    	<td>${ r.defaults }</td> 
    	<td>${ r.hardcoded }</td> 
    </tr>
    % endfor
</table>