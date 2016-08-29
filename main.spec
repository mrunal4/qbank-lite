# -*- mode: python -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['/Users/cjshaw/Documents/Projects/CLIx/qbank-lite'],
             binaries=None,
             datas=[],
             hiddenimports=['dlkit',
                            'dlkit.filesystem',
                            'dlkit.filesystem.osid.managers',
                            'dlkit.filesystem.osid.sessions',
                            'dlkit.filesystem.osid.objects',
                            'dlkit.filesystem.repository.managers',
                            'dlkit.filesystem.repository.sessions',
                            'dlkit.filesystem.repository.objects',
                            'dlkit.mongo',
                            'dlkit.mongo.assessment.managers',
                            'dlkit.mongo.assessment.sessions',
                            'dlkit.mongo.assessment.objects',
                            'dlkit.mongo.assessment_authoring.managers',
                            'dlkit.mongo.assessment_authoring.sessions',
                            'dlkit.mongo.assessment_authoring.objects',
                            'dlkit.mongo.hierarchy.managers',
                            'dlkit.mongo.hierarchy.sessions',
                            'dlkit.mongo.hierarchy.objects',
                            'dlkit.mongo.logging_.managers',
                            'dlkit.mongo.logging_.sessions',
                            'dlkit.mongo.logging_.objects',
                            'dlkit.mongo.relationship.managers',
                            'dlkit.mongo.relationship.sessions',
                            'dlkit.mongo.relationship.objects',
                            'dlkit.mongo.repository.managers',
                            'dlkit.mongo.repository.sessions',
                            'dlkit.mongo.repository.objects',
                            'dlkit.mongo.resource.managers',
                            'dlkit.mongo.resource.sessions',
                            'dlkit.mongo.resource.objects',
                            'dlkit.services',
                            'dlkit.services.assessment',
                            'dlkit.services.hierarchy',
                            'dlkit.services.logging_',
                            'dlkit.services.relationship',
                            'dlkit.services.repository',
                            'dlkit.services.resource',
                            'records',
                            'records.assessment',
                            'records.assessment.basic',
                            'records.assessment.basic.assessment_records',
                            'records.assessment.basic.base_records',
                            'records.assessment.basic.file_answer_records',
                            'records.assessment.basic.multi_choice_records',
                            'records.assessment.basic.simple_records',
                            'records.assessment.basic.wrong_answers',
                            'records.assessment.clix.assessment_offered_records',
                            'records.assessment.clix.magic_item_lookup_sessions',
                            'records.assessment.qti',
                            'records.assessment.qti.basic',
                            'records.assessment.qti.extended_text_interaction',
                            'records.assessment.qti.inline_choice_records',
                            'records.assessment.qti.numeric_response_records',
                            'records.assessment.qti.ordered_choice_records',
                            'records.logging.clix.text_blob',
                            'records.osid',
                            'records.osid.base_records',
                            'records.osid.object_records',
                            'records.fbw_dlkit_adapters.multi_choice_questions.randomized_questions'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='main',
          debug=False,
          strip=False,
          upx=True,
          console=True )
app = BUNDLE(exe,
             name='main.app',
             icon=None,
             bundle_identifier=None)
