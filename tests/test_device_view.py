"""DRM view admission against synthetic sysfs; no mount/device mutation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import uuid
spec=importlib.util.spec_from_file_location('view',Path(__file__).resolve().parents[1]/'guest/device-view.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class DeviceViewTests(unittest.TestCase):
    def test_input_selection_requires_all_unique_exact_instance_nodes(self):
        with tempfile.TemporaryDirectory() as d:
            sys=Path(d);root=sys/'class/input';root.mkdir(parents=True)
            first,second=uuid.uuid4(),uuid.uuid4()
            for number,(instance,kind) in enumerate((i,k) for i in (first,second) for k in ('Keyboard','Pointer','Wheel')):
                event=root/f'event{number}';(event/'device').mkdir(parents=True)
                (event/'device/name').write_text(f'WSX {instance} {kind}\n')
                (event/'dev').write_text(f'13:{64+number}\n')
            self.assertEqual(set(v.selected_input_nodes(second,sys)),{'event3','event4','event5'})
            (root/'event5/device/name').write_text(f'WSX {second} Keyboard\n')
            with self.assertRaises(ValueError):v.selected_input_nodes(second,sys)
    def test_exact_instance_and_sibling_render_node_only(self):
        with tempfile.TemporaryDirectory() as d:
            sys=Path(d);(sys/'bus/vmbus').mkdir(parents=True);(sys/'class/drm').mkdir(parents=True)
            instances=[uuid.uuid4(),uuid.uuid4()]
            for i,instance in enumerate(instances):
                parent=sys/'devices'/str(instance);parent.mkdir(parents=True)
                (parent/'device_id').write_text('{'+str(instance)+'}')
                (parent/'subsystem').symlink_to(sys/'bus/vmbus')
                for name,minor in [(f'card{i}',i),(f'renderD{128+i}',128+i)]:
                    p=parent/'gpu/drm'/name;p.mkdir(parents=True);(p/'dev').write_text(f'226:{minor}')
                    (sys/'class/drm'/name).symlink_to(p)
            nodes=v.selected_nodes(instances[1],'/dev/dri/card1',sys)
            self.assertEqual(set(nodes),{'card1','renderD129'})
            with self.assertRaises(ValueError):v.selected_nodes(instances[0],'/dev/dri/card1',sys)
            with self.assertRaises(ValueError):v.selected_nodes(instances[1],'/dev/dri/renderD129',sys)
