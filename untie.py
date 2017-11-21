import arcpy


def get_id_points(featureclass):
    id_points = []
    with arcpy.da.SearchCursor(featureclass, ['OID@', 'SHAPE@']) as cursor:
        for oid, line in cursor:
            point = line.positionAlongLine(0.5, use_percentage=True)
            id_points.append((oid, point))

    return id_points


def get_close_counts(id_points, close_distance):
    id_close_count = {}
    for id_num, point in id_points:
        # Initialize count of close points to zero
        if id_num not in id_close_count:
            id_close_count[id_num] = 0

        for other_id, other_point in id_points:
            if id_num != other_id:
                if point.distanceTo(other_point) < close_distance:
                    id_close_count[id_num] += 1

    return id_close_count


def get_snap_parameters(line1, line2):
    start1 = line1.positionAlongLine(0.0, use_percentage=True)
    end1 = line1.positionAlongLine(1.0, use_percentage=True)
    start2 = line2.positionAlongLine(0.0, use_percentage=True)
    end2 = line2.positionAlongLine(1.0, use_percentage=True)

    # Find out which ends are closest
    closest_distance = start1.distanceTo(end2)
    closest1 = start1
    closest2 = end2
    for p1 in (start1, end1):
        for p2 in (start2, end2):
            compare_distance = p1.distanceTo(p2)
            if compare_distance < closest_distance:
                closest_distance = compare_distance
                closest1 = p1
                closest2 = p2

    angle, distance = closest1.angleAndDistanceTo(closest2)
    mid_point = closest1.pointFromAngleAndDistance(angle, distance / 2)
    return (mid_point, distance / 2)


if __name__ == '__main__':
    trails = r'C:\GisWork\Trails\Recreation\KnotRemoval.gdb\testKnot'
    id_points = get_id_points(trails)
    close_point_counts = get_close_counts(id_points, 10)

    # Delete oids that has close mid points
    delete_oids = [str(oid) for oid in close_point_counts if close_point_counts[oid] != 0]
    delete_where_clause = 'OBJECTID IN ({})'.format(','.join(delete_oids))
    delete_layer = 'deleter'
    arcpy.MakeFeatureLayer_management(trails, delete_layer, delete_where_clause)
    arcpy.DeleteFeatures_management(delete_layer)

    # Snap oids that do not have close mid points
    lines = None
    snap_oids = [str(oid) for oid in close_point_counts if close_point_counts[oid] == 0]
    snap_where_clause = 'OBJECTID IN ({})'.format(','.join(snap_oids))
    snap_layer = 'snapper'
    arcpy.MakeFeatureLayer_management(trails, snap_layer, snap_where_clause)
    with arcpy.da.SearchCursor(snap_layer,
                               ['OID@', 'SHAPE@']) as cursor:
        lines = [line for oid, line in cursor]

    snap_point, distance = get_snap_parameters(lines[0], lines[1])
    snaps = arcpy.CopyFeatures_management(snap_point, 'in_memory\snap_point')[0]
    snap_evironment = [snaps, "VERTEX", distance + 0.1]
    arcpy.Snap_edit(snap_layer, [snap_evironment])
