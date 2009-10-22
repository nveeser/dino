# -*- coding: utf-8 -*-
<%inherit file="/master.mako"/>

<table>
	<thead>
    <tr> 
    	<th>Path</th>
    	<th>Name</th>    	 
    	<th>Conditions</th> 
    	<th>Defaults</th> 
    	<th>Hardcoded</th> 
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