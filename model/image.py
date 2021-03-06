import sys

import os

sys.path.append(os.path.realpath('..'))

from bson.json_util import dumps
from bson.objectid import ObjectId

from config.common_config import image_dir
from config.common_config import logger
from config.image_config import image_width
from config.image_config import image_height
from util.mongo_util import get_db
from util.image_util import crop
from util.image_util import morphology
from util.image_util import resize
from util.image_util import draw_rectangle
from model.storage import read_gridfs
from model.template import get_template

db = get_db()
image_collection = db['image']


class Image:
    def __init__(self, id, user_id, kind, name, template_id, regions,
                 storage_id, filename, status, create_date, update_date):
        self.id = id
        self.user_id = user_id
        self.kind = kind
        self.name = name
        self.template_id = template_id
        self.regions = regions
        self.storage_id = storage_id
        self.filename = filename
        self.status = status
        self.create_date = create_date
        self.update_date = update_date


def convert_image_from_json(data):
    obj = {}

    id = data.get('id')
    if id and ObjectId.is_valid(id):
        obj['_id'] = ObjectId(id)

    user_id = data.get('user_id')
    if user_id and ObjectId.is_valid(user_id):
        obj['user_id'] = ObjectId(user_id)

    kind = data.get('kind')
    if kind:
        obj['kind'] = kind

    name = data.get('name')
    if name:
        obj['name'] = name

    template_id = data.get('template_id')
    if template_id and ObjectId.is_valid(template_id):
        obj['template_id'] = ObjectId(template_id)

    regions = data.get('regions')
    if regions:
        obj['regions'] = regions

    storage_id = data.get('storage_id')
    if storage_id and ObjectId.is_valid(storage_id):
        obj['storage_id'] = ObjectId(storage_id)

    filename = data.get('filename')
    if filename:
        obj['filename'] = filename

    status = data.get('status')
    if status:
        obj['status'] = status

    logger.debug('--obj--' + str(obj))
    return obj


def convert_image_from_mongo(result):
    obj = {}
    obj['id'] = str(result.get('_id'))
    obj['user_id'] = str(result.get('user_id'))
    obj['kind'] = result.get('kind')
    obj['name'] = result.get('name')
    obj['template_id'] = str(result.get('template_id'))
    obj['regions'] = result.get('regions')
    obj['storage_id'] = str(result.get('storage_id'))
    obj['filename'] = result.get('filename')
    obj['status'] = result.get('status')
    return obj


def create_image(data):
    result = None
    if data:
        try:
            obj = convert_image_from_json(data)
            insert_result = image_collection.insert_one(obj)
            id = insert_result.inserted_id
            logger.debug('--id--' + str(id))
            result = get_image(id)
        except Exception as e:
            logger.debug('--create_image--' + str(e))
    return result


def get_image(id):
    result = None
    try:
        result = image_collection.find_one({'_id': id})
        logger.debug('--get_image--' + dumps(result))
    except Exception as e:
        logger.debug('--get_image--' + str(e))
    return result


def count_image(id):
    count = None
    try:
        count = image_collection.count({'_id': id})
        logger.debug('--count_image--' + dumps(count))
    except Exception as e:
        logger.debug('--count_image--' + str(e))
    return count


def exist_image(id):
    result = None
    try:
        count = image_collection.count({'_id': id})
        logger.debug('--count--' + str(count))
        if count == 0:
            result = False
        elif count == 1:
            result = True
        logger.debug('--exist_image--' + dumps(result))
    except Exception as e:
        logger.debug('--exist_image--' + str(e))
    return result


def update_image(data):
    result = None
    if data:
        try:
            obj = convert_image_from_json(data)
            id = obj.get('_id')
            logger.debug('--id--' + str(id))
            if exist_image(id):
                del obj['_id']
                image_collection.update_one({'_id': id}, {'$set': obj})
                result = get_image(id)
        except Exception as e:
            logger.debug('--update_image--' + str(e))
    return result


def delete_image(id):
    result = None
    if exist_image(id):
        try:
            image_collection.delete_one({'_id': id})
            if not exist_image(id):
                result = True
        except Exception as e:
            logger.debug('--delete_image--' + str(e))
    return result


def update_image_regions(id):
    image = get_image(id)
    if not image:
        return False

    kind = image.get('kind')
    if not kind:
        return False

    storage_id = image.get('storage_id')
    file = read_gridfs(storage_id)
    if not file:
        return False

    filename = file.filename
    bytes = file.read()

    template_id = image.get('template_id')
    template = get_template(template_id)
    if not template:
        return False

    regions = template.get('regions')
    if not regions:
        return False

    path = os.path.join(image_dir, kind, str(id))
    if not os.path.exists(path):
        os.makedirs(path)

    src_filename = os.path.join(path, filename)
    logger.debug('--src_filename--' + src_filename)
    f = open(src_filename, 'wb')
    f.write(bytes)
    f.close()

    try:
        image_collection.update_one(
            {'_id': id},
            {'$set': {'filename': filename, 'regions': regions, 'status': 'update'}}
        )
    except Exception as e:
        logger.debug('--update_image_regions--' + str(e))
        return False
    return True


def crop_image_regions(id):
    image = get_image(id)
    if not image:
        return False

    kind = image.get('kind')
    filename = image.get('filename')
    extension = filename.split('.')[-1]

    path = os.path.join(image_dir, kind, str(id))
    src_filename = os.path.join(path, filename)

    regions_path = os.path.join(path, 'regions')
    if not os.path.exists(regions_path):
        os.makedirs(regions_path)

    regions = image.get('regions')
    if not regions:
        return False

    for region in regions:
        logger.debug('--region--' + str(region))
        try:
            region_name = region.get('name') + '.' + extension
            dst_filename = os.path.join(regions_path, region_name)
            logger.debug('--dst_filename--' + dst_filename)
            pt1 = region.get('pt1')
            pt2 = region.get('pt2')
            crop(src_filename, dst_filename, pt1, pt2)
        except Exception as e:
            logger.debug('--crop_image_regions--' + str(e))
            return False

    try:
        image_collection.update_one(
            {'_id': id},
            {'$set': {'status': 'crop'}}
        )
    except Exception as e:
        logger.debug('--crop_image_regions--' + str(e))
        return False
    return True


def morphology_image_regions(id):
    image = get_image(id)
    if not image:
        return False

    kind = image.get('kind')
    filename = image.get('filename')
    extension = filename.split('.')[-1]

    path = os.path.join(image_dir, kind, str(id), 'regions')

    regions = image.get('regions')
    if not regions:
        return False

    for region in regions:
        logger.debug('--region--' + str(region))
        try:
            region_name = region.get('name') + '.' + extension
            src_filename = os.path.join(path, region_name)
            logger.debug('--src_filename--' + src_filename)
            morphology(src_filename, src_filename)
        except Exception as e:
            logger.debug('--morphology_image_regions--' + str(e))
            return False

    try:
        image_collection.update_one(
            {'_id': id},
            {'$set': {'status': 'resize'}}
        )
    except Exception as e:
        logger.debug('--resize_image_regions--' + str(e))
        return False
    return True


def resize_image_regions(id):
    image = get_image(id)
    if not image:
        return False

    kind = image.get('kind')
    filename = image.get('filename')
    extension = filename.split('.')[-1]

    path = os.path.join(image_dir, kind, str(id), 'regions')

    regions = image.get('regions')
    if not regions:
        return False

    for region in regions:
        logger.debug('--region--' + str(region))
        try:
            region_name = region.get('name') + '.' + extension
            src_filename = os.path.join(path, region_name)
            logger.debug('--src_filename--' + src_filename)
            resize(src_filename, src_filename, image_width, image_height)
        except Exception as e:
            logger.debug('--resize_image_regions--' + str(e))
            return False

    try:
        image_collection.update_one(
            {'_id': id},
            {'$set': {'status': 'resize'}}
        )
    except Exception as e:
        logger.debug('--resize_image_regions--' + str(e))
        return False
    return True


def draw_image_regions(id):
    image = get_image(id)
    if not image:
        return False

    kind = image.get('kind')
    filename = image.get('filename')

    path = os.path.join(image_dir, kind, str(id))
    src_filename = os.path.join(path, filename)

    regions = image.get('regions')
    if not regions:
        return False

    for region in regions:
        logger.debug('--region--' + str(region))
        try:
            pt1 = region.get('pt1')
            pt2 = region.get('pt2')
            draw_rectangle(src_filename, src_filename, pt1, pt2)
        except Exception as e:
            logger.debug('--draw_image_regions--' + str(e))
            return False

    try:
        image_collection.update_one(
            {'_id': id},
            {'$set': {'status': 'draw'}}
        )
    except Exception as e:
        logger.debug('--draw_image_regions--' + str(e))
        return False
    return True
