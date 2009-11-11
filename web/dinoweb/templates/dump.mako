# -*- coding: utf-8 -*-
<%inherit file="master.mako"/>

<h2>Path</h2>
<table border="1">
    % for x in c.path:
    <tr> <td>${ x }</td> </tr>
    % endfor
</table>

<h2>Dump Of Request</h2>
<table border="1">
    <tr>
        <th>Name</th>
        <th>Value</th>
    </tr>
    % for k in sorted(c.dump_obj.keys()):
    <tr>
        <td>${ k }</td>
        <td>${ c.dump_obj[k] }</td>
    </tr>
    % endfor
</table>


<h2>Dump Of Environ</h2>
<table border="1">
    <tr>
        <th>Name</th>
        <th>Value</th>
    </tr>
    % for k in sorted(c.environ.keys()):
    <tr>
        <td>${ k }</td>
        <td>${ c.environ[k] }</td>
    </tr>
    % endfor
</table>