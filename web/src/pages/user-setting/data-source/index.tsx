/*
 *  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';
import AddDataSourceModal from './add-datasource-modal';
import { AddedSourceCard } from './component/added-source-card';
import { DataSourceKey, useDataSourceInfo, CrmDataSourceKeys } from './constant';
import { useAddDataSource, useListDataSource } from './hooks';
import { IDataSorceInfo } from './interface';

const AvailableSourceCard = ({
  id,
  name,
  description,
  icon,
  onAdd,
}: IDataSorceInfo & { onAdd: () => void }) => {
  const { t } = useTranslation();
  const isCrm = CrmDataSourceKeys.includes(id as DataSourceKey);

  return (
    <article
      className={`
        size-full p-2.5 border-0.5 rounded-lg relative group hover:bg-bg-card focus-within:bg-bg-card
        grid grid-cols-[auto_1fr] grid-rows-[auto_1fr] gap-x-2.5 gap-y-1 transition-all
        ${isCrm ? 'border-primary/40 bg-primary/5 hover:border-primary/70' : 'border-border-button'}
      `}
      style={{
        gridTemplateAreas: '"icon title" "icon description"',
      }}
      onClick={() => onAdd()}
    >
      <span className="w-6" style={{ gridArea: 'icon' }}>
        {icon}
      </span>

      <header className="flex items-center gap-2" style={{ gridArea: 'title' }}>
        <h3 className="text-base text-text-primary flex items-center gap-1.5 flex-wrap">
          <span>{name}</span>
          {isCrm && (
            <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/30">
              CRM(demo)
            </span>
          )}
        </h3>

        <Button
          size="auto"
          className="ml-auto px-1 py-0.5 gap-0.5 text-xs items-center opacity-0 transition-all group-hover:opacity-100 group-focus-within:opacity-100"
          onClick={(e: any) => {
            e.stopPropagation();
            onAdd();
          }}
        >
          <Plus className="size-[1em]" />
          {t('setting.add')}
        </Button>
      </header>

      <p
        style={{ gridArea: 'description' }}
        className="text-xs text-text-secondary"
      >
        {description}
      </p>
    </article>
  );
};

const DataSource = () => {
  const { t } = useTranslation();
  const { dataSourceInfo } = useDataSourceInfo();
  const dataSourceTemplates = Object.values(DataSourceKey).map((id) => {
    return {
      id,
      name: dataSourceInfo[id].name,
      description: dataSourceInfo[id].description,
      icon: dataSourceInfo[id].icon,
    };
  });

  const crmTemplates = dataSourceTemplates.filter((item) =>
    CrmDataSourceKeys.includes(item.id as DataSourceKey),
  );
  const generalTemplates = dataSourceTemplates.filter(
    (item) => !CrmDataSourceKeys.includes(item.id as DataSourceKey),
  );

  // useListTenantUser();
  const { categorizedList } = useListDataSource();

  const {
    addSource,
    addLoading,
    addingModalVisible,
    handleAddOk,
    hideAddingModal,
    showAddingModal,
  } = useAddDataSource({});

  return (
    <ProfileSettingWrapperCard
      header={
        <header>
          <h2 className="text-2xl font-medium text-text-primary">
            {t('setting.dataSources')}
          </h2>
          <p className="mt-1 text-sm text-text-secondary ">
            {t('setting.datasourceDescription')}
          </p>
        </header>
      }
    >
      <div className="h-full p-5 overflow-x-hidden overflow-y-auto">
        <section className="flex flex-col gap-3">
          {categorizedList?.length <= 0 && (
            <div className="text-text-secondary w-full flex justify-center items-center h-20">
              {t('setting.sourceEmptyTip')}
            </div>
          )}
          {categorizedList.map((item, index) => (
            <AddedSourceCard key={index} {...item} />
          ))}
        </section>

        {/* ========================================================= */}
        {/* CRM (DEMO) DATA SOURCES SECTION */}
        {/* ========================================================= */}
        <section className="mt-8 pt-6 border-t border-border-button">
          <header className="flex flex-row items-center justify-between space-y-0 p-0 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-medium text-text-primary">
                  CRM(demo)
                </h2>
                <span className="text-xs uppercase font-semibold px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-500 border border-amber-500/30">
                  Demo rejim
                </span>
              </div>
              <div className="text-sm text-text-secondary font-normal mt-1.5">
                amoCRM, Bitrix24, 1С, HubSpot va Kommo tizimlari bilan real vaqtda sinxronizatsiya, lid yaratish va qoldiqlar tekshiruvi.
              </div>
            </div>
          </header>

          <ul className="@container grid sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-4 3xl:grid-cols-4 gap-4">
            {crmTemplates.map((item) => (
              <li key={item.id} className="h-full">
                <AvailableSourceCard
                  {...item}
                  onAdd={() => showAddingModal(item)}
                />
              </li>
            ))}
          </ul>
        </section>

        {/* ========================================================= */}
        {/* GENERAL AVAILABLE DATA SOURCES SECTION */}
        {/* ========================================================= */}
        <section className="mt-8 pt-6 border-t border-border-button">
          <header className="flex flex-row items-center justify-between space-y-0 p-0 pb-4">
            <h2 className="text-2xl font-medium">
              {t('setting.availableSources')}
              <div className="text-sm text-text-secondary font-normal mt-1.5">
                {t('setting.availableSourcesDescription')}
              </div>
            </h2>
          </header>

          <ul className="@container grid sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-4 3xl:grid-cols-4 gap-4">
            {generalTemplates.map((item) => (
              <li key={item.id} className="h-full">
                <AvailableSourceCard
                  {...item}
                  onAdd={() => showAddingModal(item)}
                />
              </li>
            ))}
          </ul>
        </section>
      </div>

      {addingModalVisible && (
        <AddDataSourceModal
          visible
          loading={addLoading}
          hideModal={hideAddingModal}
          onOk={(data) => {
            return handleAddOk(data);
          }}
          sourceData={addSource}
        />
      )}
    </ProfileSettingWrapperCard>
  );
};

export default DataSource;
