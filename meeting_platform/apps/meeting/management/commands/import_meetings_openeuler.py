import logging

from django.core.management.base import BaseCommand

from meeting_platform.apps.meeting.management.model.models import OldMeeting, OldRecord, Video
from meeting_platform.apps.meeting.models import Meeting, MeetingBiliRecords, MeetingObsRecords

logger = logging.getLogger('log')


class Command(BaseCommand):
    help = 'Import meetings from openEuler platform'

    def handle(self, *args, **options):
        import_type = options.get('type', 'all')

        try:
            if import_type in ['all', 'meetings']:
                self.import_meetings()

            if import_type in ['all', 'records']:
                self.import_meeting_records()

            self.stdout.write(self.style.SUCCESS('Successfully imported data from openEuler platform'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to import: {e}'))
            logger.error(f'Failed to import: {e}', exc_info=True)

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='all',
            choices=['all', 'meetings', 'records'],
            help='Import type: all (default), meetings, or records',
        )

    def import_meetings(self):
        """Import meetings from OldMeeting (meetings_meeting table) to Meeting (meetings table)"""
        old_meetings = OldMeeting.objects.using('openeuler_meetings').all()
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for old_meeting in old_meetings:
            try:
                # Check if meeting already exists
                existing_meeting = Meeting.objects.filter(mid=old_meeting.mid).first()

                # Map fields from OldMeeting to Meeting
                meeting_data = {
                    'sponsor': old_meeting.sponsor[:64],
                    'group_name': old_meeting.group_name[:64],
                    'community': old_meeting.community[:16] if old_meeting.community else '',
                    'topic': old_meeting.topic[:128],
                    'platform': old_meeting.mplatform,
                    'is_cycle': 0,
                    'date': old_meeting.date,
                    'start': old_meeting.start,
                    'end': old_meeting.end,
                    'agenda': old_meeting.agenda or '',
                    'etherpad': old_meeting.etherpad[:256] if old_meeting.etherpad else None,
                    'email_list': old_meeting.emaillist,
                    'host_id': old_meeting.host_id,
                    'mid': old_meeting.mid,
                    'm_mid': old_meeting.mmid,
                    'join_url': old_meeting.join_url[:128] if old_meeting.join_url else None,
                    'is_record': old_meeting.is_delete,
                    'create_time': old_meeting.create_time,
                    'is_delete': old_meeting.is_delete,
                    'sequence': 1,
                }

                if existing_meeting:
                    # Update existing meeting
                    for key, value in meeting_data.items():
                        setattr(existing_meeting, key, value)
                    existing_meeting.save()
                    updated_count += 1
                    logger.info(f'Updated meeting: {old_meeting.mid}')
                else:
                    # Create new meeting
                    Meeting.objects.create(**meeting_data)
                    created_count += 1
                    logger.info(f'Created meeting: {old_meeting.mid}')

            except Exception as e:
                logger.error(f'Failed to import meeting {old_meeting.mid}: {e}', exc_info=True)
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed: {created_count} created, {updated_count} updated, {skipped_count} skipped'
            )
        )

    def import_meeting_records(self):
        """Import meeting records from meetings_record and meetings_video to MeetingBiliRecords/MeetingObsRecords"""
        old_records = OldRecord.objects.using('openeuler_meetings').all()
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for old_record in old_records:
            try:
                # Validate required field: mid
                if not old_record.mid:
                    logger.warning(f'Record has empty mid, skipping')
                    skipped_count += 1
                    continue

                # Find the associated meeting
                meeting = Meeting.objects.filter(mid=old_record.mid).first()
                if not meeting:
                    logger.warning(f'Meeting not found for mid: {old_record.mid}, skipping record import')
                    skipped_count += 1
                    continue

                # Determine target table based on platform
                platform = old_record.platform.lower() if old_record.platform else ''

                if 'bili' in platform:
                    # Import to MeetingBiliRecords
                    existing_record = MeetingBiliRecords.objects.filter(
                        mid=old_record.mid, sub_id__isnull=True
                    ).first()

                    record_data = {
                        'mid': old_record.mid[:32],
                        'sub_id': None,
                        'status': 10,  # UploadStatus.FINISH
                        'replay_url': old_record.url[:128] if old_record.url else None,
                        'meeting': meeting,
                    }

                    if existing_record:
                        for key, value in record_data.items():
                            setattr(existing_record, key, value)
                        existing_record.save()
                        updated_count += 1
                        logger.info(f'Updated bili record: {old_record.mid}')
                    else:
                        MeetingBiliRecords.objects.create(**record_data)
                        created_count += 1
                        logger.info(f'Created bili record: {old_record.mid}')

                elif 'obs' in platform:
                    # Import to MeetingObsRecords
                    # Merge data from meetings_record and meetings_video by mid
                    video = Video.objects.using('openeuler_meetings').filter(mid=old_record.mid).first()

                    existing_record = MeetingObsRecords.objects.filter(
                        mid=old_record.mid, sub_id__isnull=True
                    ).first()

                    record_data = {
                        'mid': old_record.mid[:32],
                        'sub_id': None,
                        'status': 10,  # UploadStatus.FINISH
                        'text_vtt_url': video.text_vtt_url[:255] if video and video.text_vtt_url else None,
                        'text_json_url': video.text_json_url[:255] if video and video.text_json_url else None,
                        'text_video_url': video.text_video_url[:255] if video and video.text_video_url else None,
                        'text_picture_url': old_record.thumbnail[:255] if old_record.thumbnail else None,
                        'topic_url': old_record.url[:255] if old_record.url else None,
                        'meeting': meeting,
                    }

                    if existing_record:
                        for key, value in record_data.items():
                            setattr(existing_record, key, value)
                        existing_record.save()
                        updated_count += 1
                        logger.info(f'Updated obs record: {old_record.mid}')
                    else:
                        MeetingObsRecords.objects.create(**record_data)
                        created_count += 1
                        logger.info(f'Created obs record: {old_record.mid}')

                else:
                    logger.warning(f'Unknown platform: {platform} for mid: {old_record.mid}, skipping')
                    skipped_count += 1

            except Exception as e:
                logger.error(f'Failed to import record {old_record.mid}: {e}', exc_info=True)
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Records import completed: {created_count} created, {updated_count} updated, {skipped_count} skipped'
            )
        )
