select object_id
  , properties ->> 'Street' as street
  , properties ->> 'Intersecti' as intersection
  , properties ->> 'SignalType' as signal_type
  , properties

from preview_pag_bikemap_features
where 1=1
  and layer_name = 'Push Button Crossings'
order by signal_type, street
