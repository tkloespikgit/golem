import logging
import math
import os
import random
from collections import OrderedDict

from PIL import Image, ImageChops

from golem.core.common import get_golem_path
from golem.task.taskstate import SubtaskStatus

from apps.blender.blenderenvironment import BlenderEnvironment
from apps.blender.resources.scenefileeditor import generate_blender_crop_file
from apps.core.task.coretask import TaskTypeInfo
from apps.rendering.resources.renderingtaskcollector import RenderingTaskCollector, exr_to_pil
from apps.rendering.task.framerenderingtask import FrameRenderingTask, FrameRenderingTaskBuilder, FrameRendererOptions
from apps.rendering.task.renderingtaskstate import RenderingTaskDefinition
from golem.resource.dirmanager import get_test_task_path, find_task_script
from apps.rendering.task.renderingtask import AcceptClientVerdict
from apps.rendering.task.renderingtaskstate import RendererDefaults


logger = logging.getLogger("apps.blender")

APP_DIR = os.path.join(get_golem_path(), 'apps', 'blender')


class BlenderDefaults(RendererDefaults):
    def __init__(self):
        RendererDefaults.__init__(self)
        self.output_format = "EXR"

        self.main_program_file = find_task_script(APP_DIR, "docker_blendertask.py")
        self.min_subtasks = 1
        self.max_subtasks = 100
        self.default_subtasks = 6


class PreviewUpdater(object):
    def __init__(self, preview_file_path, preview_res_x, preview_res_y, expected_offsets):
        # pairs of (subtask_number, its_image_filepath)
        # careful: chunks' numbers start from 1
        self.chunks = {}
        self.preview_res_x = preview_res_x
        self.preview_res_y = preview_res_y
        self.preview_file_path = preview_file_path
        self.expected_offsets = expected_offsets
        
        # where the match ends - since the chunks have unexpectable sizes, we 
        # don't know where to paste new chunk unless all of the above are in 
        # their correct places
        self.perfect_match_area_y = 0
        self.perfectly_placed_subtasks = 0

    def get_offset(self, subtask_number):
        if 0 < subtask_number < len(self.expected_offsets):
            return self.expected_offsets[subtask_number]
        return self.preview_res_y

    def update_preview(self, subtask_path, subtask_number):
        if subtask_number not in self.chunks:
            self.chunks[subtask_number] = subtask_path
        
        try:
            if subtask_path.upper().endswith(".EXR"):
                img = exr_to_pil(subtask_path)
            else:
                img = Image.open(subtask_path)

            offset = self.get_offset(subtask_number)
            if subtask_number == self.perfectly_placed_subtasks + 1:
                _, img_y = img.size
                self.perfect_match_area_y += img_y
                self.perfectly_placed_subtasks += 1

            # this is the last task
            if subtask_number + 1 >= len(self.expected_offsets):
                height = self.preview_res_y - self.expected_offsets[subtask_number]
            else:
                height = self.expected_offsets[subtask_number + 1] - self.expected_offsets[subtask_number]
            
            img = img.resize((self.preview_res_x, height), resample=Image.BILINEAR)
            if not os.path.exists(self.preview_file_path) or len(self.chunks) == 1:
                img_offset = Image.new("RGB", (self.preview_res_x, self.preview_res_y))
                img_offset.paste(img, (0, offset))
                img_offset.save(self.preview_file_path, "BMP")
                img_offset.close()
            else:
                img_current = Image.open(self.preview_file_path)
                img_current.paste(img, (0, offset))
                img_current.save(self.preview_file_path, "BMP")
                img_current.close()
            img.close()

        except Exception as err:
            import traceback
            # Print the stack traceback
            traceback.print_exc()
            return
        
        if subtask_number == self.perfectly_placed_subtasks and (subtask_number + 1) in self.chunks:
            self.update_preview(self.chunks[subtask_number + 1], subtask_number + 1)

    def restart(self):
        self.chunks = {}
        self.perfect_match_area_y = 0
        self.perfectly_placed_subtasks = 0
        if os.path.exists(self.preview_file_path):
            img = Image.new("RGB", (self.preview_res_x, self.preview_res_y))
            img.save(self.preview_file_path, "BMP")
            img.close()


class BlenderTaskTypeInfo(TaskTypeInfo):
    """ Blender App descryption that can be used by interface to define
    parameters and task build
    """
    def __init__(self, dialog, customizer):
        super(BlenderTaskTypeInfo, self).__init__("Blender",
                                                  RenderingTaskDefinition,
                                                  BlenderDefaults(),
                                                  BlenderRendererOptions,
                                                  BlenderRenderTaskBuilder,
                                                  dialog,
                                                  customizer)

        self.output_formats = ["PNG", "TGA", "EXR", "JPEG", "BMP"]
        self.output_file_ext = ["blend"]

    @classmethod
    def get_task_border(cls, subtask, definition, total_subtasks,
                        output_num=1):
        """ Return list of pixels that should be marked as a border of
         a given subtask
        :param SubtaskState subtask: subtask state description
        :param RenderingTaskDefinition definition: task definition
        :param int total_subtasks: total number of subtasks used in this task
        :param int output_num: number of final output files
        :return list: list of pixels that belong to a subtask border
        """
        start_task = subtask.extra_data['start_task']
        end_task = subtask.extra_data['end_task']
        frames = len(definition.options.frames)
        res_x, res_y = definition.resolution

        if not definition.options.use_frames:
            return cls.__get_border(start_task, end_task, total_subtasks, res_x, res_y)

        if total_subtasks > frames:
            parts = total_subtasks / frames
            return cls.__get_border((start_task - 1) % parts + 1, (end_task - 1) % parts + 1,
                                    parts, res_x, res_y)

        return []

    @classmethod
    def __get_border(cls, start, end, parts, res_x, res_y):
        """
        Return list of pixels that should be marked as a border of subtasks
        with numbers between start and end.
        :param int start: number of first subtask
        :param int end: number of last subtask
        :param int parts: number of parts for single frame
        :param int res_x: image resolution width
        :param int res_y: image resolution height
        :return list: list of pixels that belong to a subtask border
        """
        border = []
        if res_x == 0 or res_y == 0:
            return border
        offsets = generate_expected_offsets(parts, res_x, res_y)
        scale_factor = float(offsets[parts + 1]) / res_y

        upper = offsets[start]
        lower = offsets[end + 1]
        for i in range(upper, lower):
            border.append((0, i))
            border.append((int(math.floor(res_x * scale_factor)), i))
        for i in range(0, int(math.floor(res_x * scale_factor))):
            border.append((i, upper))
            border.append((i, lower))
        return border

    @classmethod
    def get_task_num_from_pixels(cls, x, y, definition, total_subtasks,
                                 output_num=1):
        """
        Compute number of subtask that represents pixel (x, y) on preview
        :param int x: x coordinate
        :param int y: y coordiante
        :param TaskDefintion definition: task definition
        :param int total_subtasks: total number of subtasks used in this task
        :param int output_num: number of final output files
        :return int: subtask's number
        """

        res_x = definition.resolution[0]
        res_y = definition.resolution[1]

        if not definition.options.use_frames:
            return cls.__num_from_pixel(y, res_x, res_y, total_subtasks)

        frames = len(definition.options.frames)
        if total_subtasks <= frames:
            subtask_frames = int(math.ceil(float(frames) / total_subtasks))
            return int(math.ceil(float(output_num) / subtask_frames))

        parts = total_subtasks / frames
        return (output_num - 1) * parts + cls.__num_from_pixel(y, res_x,
                                                               res_y, parts)

    @classmethod
    def __num_from_pixel(cls, p_y, res_x, res_y, parts):
        """
        Compute number of subtask that represents pixel with y coordiante equal
        to py on preview with given resolution
        :param int p_y: y coordinate of a pixel
        :param int res_x: image width
        :param int res_y: image height
        :param int parts: number of parts on one frame
        :return:
        """
        offsets = generate_expected_offsets(parts, res_x, res_y)
        for task_num in range(1, parts + 1):
            low = offsets[task_num]
            high = offsets[task_num + 1]
            if low <= p_y < high:
                return task_num
        return parts


class BlenderRendererOptions(FrameRendererOptions):
    def __init__(self):
        super(BlenderRendererOptions, self).__init__()
        self.environment = BlenderEnvironment()
        self.compositing = False


class BlenderRenderTaskBuilder(FrameRenderingTaskBuilder):
    """ Build new Blender tasks using RenderingTaskDefintions and BlenderRendererOptions as taskdefinition
    renderer options
    """
    def build(self):
        main_scene_dir = os.path.dirname(self.task_definition.main_scene_file)
        if self.task_definition.docker_images is None:
            self.task_definition.docker_images = BlenderEnvironment().docker_images

        blender_task = BlenderRenderTask(self.node_name,
                                         self.task_definition.task_id,
                                         main_scene_dir,
                                         self.task_definition.main_scene_file,
                                         self.task_definition.main_program_file,
                                         self._calculate_total(BlenderDefaults(), self.task_definition),
                                         self.task_definition.resolution[0],
                                         self.task_definition.resolution[1],
                                         os.path.splitext(os.path.basename(self.task_definition.output_file))[0],
                                         self.task_definition.output_file,
                                         self.task_definition.output_format,
                                         self.task_definition.full_task_timeout,
                                         self.task_definition.subtask_timeout,
                                         self.task_definition.resources,
                                         self.task_definition.estimated_memory,
                                         self.root_path,
                                         self.task_definition.options.use_frames,
                                         self.task_definition.options.frames,
                                         self.task_definition.options.compositing,
                                         self.task_definition.max_price,
                                         docker_images=self.task_definition.docker_images)
        self._set_verification_options(blender_task)
        blender_task.initialize(self.dir_manager)
        return blender_task

    def _set_verification_options(self, new_task):
        new_task = FrameRenderingTaskBuilder._set_verification_options(self, new_task)
        if new_task.advanceVerification:
            box_x = min(new_task.verification_options.box_size[0], new_task.res_x)
            box_y = min(new_task.verification_options.box_size[1], new_task.res_y / new_task.total_tasks)
            new_task.box_size = (box_x, box_y)
        return new_task


DEFAULT_BLENDER_DOCKER_IMAGE = "golemfactory/blender:1.3"


class BlenderRenderTask(FrameRenderingTask):

    ################
    # Task methods #
    ################

    def __init__(self,
                 node_name,
                 task_id,
                 main_scene_dir,
                 main_scene_file,
                 main_program_file,
                 total_tasks,
                 res_x,
                 res_y,
                 outfilebasename,
                 output_file,
                 output_format,
                 full_task_timeout,
                 subtask_timeout,
                 task_resources,
                 estimated_memory,
                 root_path,
                 use_frames,
                 frames,
                 compositing,
                 max_price,
                 return_address="",
                 return_port=0,
                 key_id="",
                 docker_images=None):

        FrameRenderingTask.__init__(self, node_name, task_id, return_address, return_port, key_id,
                                    BlenderEnvironment.get_id(), full_task_timeout, subtask_timeout,
                                    main_program_file, task_resources, main_scene_dir, main_scene_file,
                                    total_tasks, res_x, res_y, outfilebasename, output_file, output_format,
                                    root_path, estimated_memory, use_frames, frames, max_price, docker_images)

        self.compositing = compositing
        self.frames_given = {}
        for frame in frames:
            frame_key = unicode(frame)
            self.frames_given[frame_key] = {}

        self.preview_updater = None
        self.preview_updaters = None

    def initialize(self, dir_manager):
        super(BlenderRenderTask, self).initialize(dir_manager)

        if self.use_frames:
            parts = self.total_tasks / len(self.frames)
        else:
            parts = self.total_tasks
        expected_offsets = generate_expected_offsets(parts, self.res_x, self.res_y)
        preview_y = expected_offsets[parts + 1]
        if self.res_y != 0 and preview_y != 0:
            self.scale_factor = float(preview_y) / self.res_y

        if self.use_frames:
            self.preview_file_path = []
            self.preview_updaters = []
            for i in range(0, len(self.frames)):
                preview_path = os.path.join(self.tmp_dir, "current_task_preview{}".format(i))
                self.preview_file_path.append(preview_path)
                self.preview_updaters.append(PreviewUpdater(preview_path, 
                                                            int(round(self.res_x * self.scale_factor)),
                                                            preview_y, 
                                                            expected_offsets))
        else:
            self.preview_file_path = "{}".format(os.path.join(self.tmp_dir, "current_preview"))
            self.preview_updater = PreviewUpdater(self.preview_file_path, 
                                                  int(round(self.res_x * self.scale_factor)), 
                                                  preview_y, 
                                                  expected_offsets)

    def query_extra_data(self, perf_index, num_cores=0, node_id=None, node_name=None):

        verdict = self._accept_client(node_id)
        if verdict != AcceptClientVerdict.ACCEPTED:

            should_wait = verdict == AcceptClientVerdict.SHOULD_WAIT
            if should_wait:
                logger.warning("Waiting for results from {}".format(node_name))
            else:
                logger.warning("Client {} banned from this task".format(node_name))

            return self.ExtraData(should_wait=should_wait)

        start_task, end_task = self._get_next_task()
        working_directory = self._get_working_directory()
        scene_file = self._get_scene_file_rel_path()

        if self.use_frames:
            frames, parts = self._choose_frames(self.frames, start_task, self.total_tasks)
        else:
            frames = [1]
            parts = 1

        if not self.use_frames:
            min_y, max_y = self._get_min_max_y(start_task)
        elif parts > 1:
            min_y = (parts - self._count_part(start_task, parts)) * (1.0 / float(parts))
            max_y = (parts - self._count_part(start_task, parts) + 1) * (1.0 / float(parts))
        else:
            min_y = 0.0
            max_y = 1.0

        script_src = generate_blender_crop_file(
            resolution=(self.res_x, self.res_y),
            borders_x=(0.0, 1.0),
            borders_y=(min_y, max_y),
            use_compositing=self.compositing
        )

        extra_data = {"path_root": self.main_scene_dir,
                      "start_task": start_task,
                      "end_task": end_task,
                      "total_tasks": self.total_tasks,
                      "outfilebasename": self.outfilebasename,
                      "scene_file": scene_file,
                      "script_src": script_src,
                      "frames": frames,
                      "output_format": self.output_format
                      }

        hash = "{}".format(random.getrandbits(128))
        self.subtasks_given[hash] = extra_data
        self.subtasks_given[hash]['status'] = SubtaskStatus.starting
        self.subtasks_given[hash]['perf'] = perf_index
        self.subtasks_given[hash]['node_id'] = node_id
        self.subtasks_given[hash]['parts'] = parts

        if not self.use_frames:
            self._update_task_preview()
        else:
            self._update_frame_task_preview()

        ctd = self._new_compute_task_def(hash, extra_data, working_directory, perf_index)
        return self.ExtraData(ctd=ctd)

    def restart(self):
        super(BlenderRenderTask, self).restart()
        if self.use_frames:
            for preview in self.preview_updaters:
                preview.restart()
                self._update_frame_task_preview()
        else:
            self.preview_updater.restart()
            self._update_task_preview()

    ###################
    # CoreTask methods #
    ###################

    def query_extra_data_for_test_task(self):

        working_directory = self._get_working_directory()
        scene_file = self._get_scene_file_rel_path()

        if self.use_frames:
            frames = [self.frames[0]]
            if len(self.frames) > 1:
                frames.append(max(self.frames))
        else:
            frames = [1]

        script_src = generate_blender_crop_file(
            resolution=(8, 8),
            borders_x=(0.0, 1.0),
            borders_y=(0.0, 1.0),
            use_compositing=self.compositing
        )

        extra_data = {"path_root": self.main_scene_dir,
                      "start_task": 1,
                      "end_task": 1,
                      "total_tasks": self.total_tasks,
                      "outfilebasename": self.outfilebasename,
                      "scene_file": scene_file,
                      "script_src": script_src,
                      "frames": frames,
                      "output_format": self.output_format
                      }

        hash = "{}".format(random.getrandbits(128))

        self.test_task_res_path = get_test_task_path(self.root_path)
        logger.debug(self.test_task_res_path)
        if not os.path.exists(self.test_task_res_path):
            os.makedirs(self.test_task_res_path)

        return self._new_compute_task_def(hash, extra_data, working_directory, 0)

    def query_extra_data_for_advance_verification(self, extra_data):
        ctd = self.query_extra_data_for_test_task()
        ctd.extra_data = extra_data
        return ctd

    def _get_min_max_y(self, start_task):
        if self.use_frames:
            parts = self.total_tasks / len(self.frames)
        else:
            parts = self.total_tasks
        return get_min_max_y(start_task, parts, self.res_y)

    def _get_part_size(self, subtask_id):
        start_task = self.subtasks_given[subtask_id]['start_task']
        if not self.use_frames:
            res_y = self._get_part_size_from_subtask_number(start_task)
        elif len(self.frames) >= self.total_tasks:
            res_y = self.res_y
        else:
            parts = self.total_tasks / len(self.frames)
            res_y = int(math.floor(float(self.res_y) / float(parts)))
        return self.res_x, res_y

    def _get_part_size_from_subtask_number(self, subtask_number):
        
        if self.res_y % self.total_tasks == 0:
            res_y = self.res_y / self.total_tasks
        else:
            # in this case task will be divided into not equal parts: floor or ceil of (res_y/total_tasks)
            # ceiling will be height of subtasks with smaller num
            ceiling_height = int(math.ceil(float(self.res_y) / float(self.total_tasks)))
            ceiling_subtasks = self.total_tasks - (ceiling_height * self.total_tasks - self.res_y)
            if subtask_number > ceiling_subtasks:
                res_y = ceiling_height - 1
            else:
                res_y = ceiling_height
        return res_y

    @FrameRenderingTask.handle_key_error
    def _get_part_img_size(self, subtask_id, adv_test_file):
        x, y = self._get_part_size(subtask_id)
        return 0, 0, x, y

    @FrameRenderingTask.handle_key_error
    def _change_scope(self, subtask_id, start_box, tr_file):
        extra_data, _ = FrameRenderingTask._change_scope(self, subtask_id, start_box, tr_file)
        min_x = start_box[0] / float(self.res_x)
        max_x = (start_box[0] + self.verification_options.box_size[0] + 1) / float(self.res_x)
        start_y = start_box[1] + (extra_data['start_task'] - 1) * (self.res_y / float(extra_data['total_tasks']))
        max_y = float(self.res_y - start_y) / self.res_y
        min_y = max(float(self.res_y - start_y - self.verification_options.box_size[1] - 1) / self.res_y, 0.0)
        script_src = generate_blender_crop_file(
            resolution=(self.res_x, self.res_y),
            borders_x=(min_x, max_x),
            borders_y=(min_y, max_y),
            use_compositing=self.compositing
        )
        extra_data['script_src'] = script_src
        extra_data['output_format'] = self.output_format
        return extra_data, (0, 0)

    def after_test(self, results, tmp_dir):
        ret = []
        if results and results.get("data"):
            for filename in results["data"]:
                if filename.lower().endswith(".log"):
                    with open(filename, "r") as fd:
                        warnings = self.__find_missing_files_warnings(fd.read())
                        fd.close()
                        for w in warnings:
                            if w not in ret:
                                ret.append(w)

        return ret

    def __find_missing_files_warnings(self, log_content):
        warnings = []
        for l in log_content.splitlines():
            if l.lower().startswith("warning: path ") and l.lower().endswith(" not found"):
                # extract filename from warning message
                warnings.append(os.path.basename(l[14:-11]))
        return warnings

    def __get_frame_num_from_output_file(self, file_):
        file_name = os.path.basename(file_)
        file_name, ext = os.path.splitext(file_name)
        idx = file_name.find(self.outfilebasename)
        return int(file_name[idx + len(self.outfilebasename):])

    def _update_preview(self, new_chunk_file_path, chunk_num):
        self.preview_updater.update_preview(new_chunk_file_path, chunk_num)

    def _update_frame_preview(self, new_chunk_file_path, frame_num, part=1, final=False):
        if final:
            if new_chunk_file_path.upper().endswith(".EXR"):
                img = exr_to_pil(new_chunk_file_path)
            else:   
                img = Image.open(new_chunk_file_path)
            scaled = img.resize((int(round(self.res_x * self.scale_factor)), int(round(self.res_y * self.scale_factor))), 
                                resample=Image.BILINEAR)
            scaled.save(self.preview_file_path[self.frames.index(frame_num)], "BMP")
            scaled.save(self.preview_task_file_path[self.frames.index(frame_num)], "BMP")
            scaled.close()
            img.close()
        else:
            self.preview_updaters[self.frames.index(frame_num)].update_preview(new_chunk_file_path, part)
            self._update_frame_task_preview()
    
    def _put_image_together(self):
        output_file_name = u"{}".format(self.output_file, self.output_format)
        self.collected_file_names = OrderedDict(sorted(self.collected_file_names.items()))
        if not self._use_outer_task_collector():
            collector = CustomCollector(paste=True, width=self.res_x, height=self.res_y)
            for file in self.collected_file_names.values():
                collector.add_img_file(file)
            collector.finalize().save(output_file_name, self.output_format)
        else:
            self._put_collected_files_together(os.path.join(self.tmp_dir, output_file_name),
                                               self.collected_file_names.values(), "paste")
            
    def mark_part_on_preview(self, part, img_task, color, preview_updater, frame_index=0):
        lower = preview_updater.get_offset(part)
        upper = preview_updater.get_offset(part + 1)
        res_x = preview_updater.preview_res_x
        for i in range(0, res_x):
                for j in range(lower, upper):
                    img_task.putpixel((i, j), color)

    def _mark_task_area(self, subtask, img_task, color, frame_index=0):
        if not self.use_frames:
            self.mark_part_on_preview(subtask['start_task'], img_task, color, self.preview_updater)
        elif self.total_tasks <= len(self.frames):
            for i in range(0, int(math.floor(self.res_x * self.scale_factor))):
                for j in range(0, int(math.floor(self.res_y * self.scale_factor))):
                    img_task.putpixel((i, j), color)
        else:
            parts = self.total_tasks / len(self.frames)
            pu = self.preview_updaters[frame_index]
            part = (subtask['start_task'] - 1) % parts + 1
            self.mark_part_on_preview(part, img_task, color, pu)

    def _put_frame_together(self, frame_num, num_start):
        directory = os.path.dirname(self.output_file)
        output_file_name = os.path.join(directory, self._get_output_name(frame_num))
        frame_key = unicode(frame_num)
        collected = self.frames_given[frame_key]
        collected = OrderedDict(sorted(collected.items()))
        if not self._use_outer_task_collector():
            collector = CustomCollector(paste=True, width=self.res_x, height=self.res_y)
            for file in collected.values():
                collector.add_img_file(file)
            collector.finalize().save(output_file_name, self.output_format)
        else:
            self._put_collected_files_together(output_file_name, collected.values(), "paste")
        self.collected_file_names[frame_num] = output_file_name
        self._update_frame_preview(output_file_name, frame_num, final=True)
        self._update_frame_task_preview()


class CustomCollector(RenderingTaskCollector):
    def __init__(self, paste=False, width=1, height=1):
        RenderingTaskCollector.__init__(self, paste, width, height)
        self.current_offset = 0
    
    def _paste_image(self, final_img, new_part, num):
        img_offset = Image.new("RGB", (self.width, self.height))
        offset = self.current_offset
        _, new_img_res_y = new_part.size
        self.current_offset += new_img_res_y
        img_offset.paste(new_part, (0, offset))
        result = ImageChops.add(final_img, img_offset)
        img_offset.close()
        return result


def generate_expected_offsets(parts, res_x, res_y):
    # returns expected offsets for preview; the highest value is preview's height
    scale_factor = __scale_factor(res_x, res_y)
    expected_offsets = [0]
    previous_end = 0
    for i in range(1, parts + 1):
        low, high = get_min_max_y(i, parts, res_y) 
        low *= scale_factor * res_y
        high *= scale_factor * res_y
        height = int(math.floor(high - low))
        expected_offsets.append(previous_end)
        previous_end += height
    
    expected_offsets.append(previous_end)
    return expected_offsets


def get_min_max_y(task_num, parts, res_y):
    if res_y % parts == 0:
        min_y = (parts - task_num) * (1.0 / float(parts))
        max_y = (parts - task_num + 1) * (1.0 / float(parts))
    else:
        ceiling_height = int(math.ceil(float(res_y) / float(parts)))
        ceiling_subtasks = parts - (ceiling_height * parts - res_y)
        if task_num > ceiling_subtasks:
            min_y = float(parts - task_num) * float(ceiling_height - 1) / float(res_y)
            max_y = float(parts - task_num + 1) * float(ceiling_height - 1) / float(res_y)
        else:
            min_y = (parts - ceiling_subtasks) * (ceiling_height - 1)
            min_y += (ceiling_subtasks - task_num) * ceiling_height
            min_y = float(min_y) / float(res_y)

            max_y = (parts - ceiling_subtasks) * (ceiling_height - 1)
            max_y += (ceiling_subtasks - task_num + 1) * ceiling_height
            max_y = float(max_y) / float(res_y)
    return min_y, max_y





def __scale_factor(res_x, res_y):
    preview_x = 300
    preview_y = 200
    if res_x != 0 and res_y != 0:
        if float(res_x) / float(res_y) > float(preview_x) / float(preview_y):
            scale_factor = float(preview_x) / float(res_x)
        else:
            scale_factor = float(preview_y) / float(res_y)
        scale_factor = min(1.0, scale_factor)
    else:
        scale_factor = 1.0
    return scale_factor
    

