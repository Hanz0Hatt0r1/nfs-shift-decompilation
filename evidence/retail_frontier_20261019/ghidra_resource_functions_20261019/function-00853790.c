
undefined4 * __thiscall FUN_00853790(void *this,int *param_1)

{
  longlong lVar1;
  int *piVar2;
  bool bVar3;
  undefined4 uVar4;
  int *piVar5;
  uint uVar6;
  undefined4 local_44;
  undefined4 local_40;
  undefined1 local_3c;
  undefined1 local_3b;
  undefined1 local_3a;
  undefined1 local_39;
  undefined4 local_38;
  undefined4 local_34;
  undefined4 local_30;
  undefined4 local_2c;
  undefined4 local_28;
  undefined1 local_24;
  undefined1 local_20;
  undefined4 local_1c;
  undefined1 local_c [4];
  int local_8;

  FUN_0082d190(this);
  FUN_00839e10((undefined4 *)((int)this + 4));
  piVar2 = param_1;
  *(undefined ***)this = &PTR_GetInt_00b1c320;
  *(int *)((int)this + 8) = *param_1;
  *(int *)((int)this + 0xc) = param_1[1];
  *(int *)((int)this + 0x10) = param_1[2];
  uVar4 = FUN_0082ecc0(param_1[3]);
  *(undefined4 *)((int)this + 0x14) = uVar4;
  uVar4 = FUN_0082ed80(piVar2[4]);
  *(undefined4 *)((int)this + 0x18) = uVar4;
  *(char *)((int)this + 0x1c) = (char)piVar2[5];
  *(undefined1 *)((int)this + 0x1d) = *(undefined1 *)((int)piVar2 + 0x15);
  *(undefined1 *)((int)this + 0x1e) = *(undefined1 *)((int)piVar2 + 0x16);
  *(int *)((int)this + 0x20) = piVar2[6];
  *(int *)((int)this + 0x28) = piVar2[8];
  *(undefined4 *)((int)this + 0x30) = 0;
  *(undefined4 *)((int)this + 0x34) = 0;
  *(undefined4 *)((int)this + 0x38) = 0;
  *(undefined4 *)((int)this + 0x3c) = 0;
  *(undefined4 *)((int)this + 0x40) = 0;
  *(undefined1 *)((int)this + 0x44) = 0;
  *(undefined1 *)((int)this + 0x45) = 0;
  *(undefined4 *)((int)this + 0x48) = 0;
  *(undefined4 *)((int)this + 0x4c) = 0;
  *(undefined1 *)((int)this + 0x50) = 0;
  *(undefined1 *)((int)this + 0x51) = 0;
  if (*(int *)((int)this + 8) == 0) {
    *(int *)((int)this + 0x24) = piVar2[7];
    *(int *)((int)this + 0x2c) = piVar2[7];
  }
  else if (*(int *)((int)this + 8) == 1) {
    *(undefined4 *)((int)this + 0x24) = 1;
    *(undefined4 *)((int)this + 0x2c) = 6;
  }
  if (*(int *)((int)this + 0x24) != 0) {
    lVar1 = (ulonglong)*(uint *)((int)this + 0x2c) * 4;
    uVar4 = FUN_008868c0(-(uint)((int)((ulonglong)lVar1 >> 0x20) != 0) | (uint)lVar1);
    *(undefined4 *)((int)this + 0x30) = uVar4;
    lVar1 = (ulonglong)*(uint *)((int)this + 0x24) * 4;
    uVar4 = FUN_008868c0(-(uint)((int)((ulonglong)lVar1 >> 0x20) != 0) | (uint)lVar1);
    *(undefined4 *)((int)this + 0x38) = uVar4;
    if (piVar2[10] == 0) {
      FUN_008243e0(&local_44);
      local_44 = *(undefined4 *)((int)this + 8);
      local_40 = FUN_0082f190(*(uint *)((int)this + 0x14));
      local_38 = *(undefined4 *)((int)this + 0xc);
      local_34 = *(undefined4 *)((int)this + 0x10);
      local_39 = *(undefined1 *)((int)this + 0x1d);
      local_30 = 1;
      local_1c = 1;
      local_20 = *(undefined1 *)((int)this + 0x1c);
      uVar6 = 0;
      local_3c = 1;
      local_3b = 1;
      local_3a = 0;
      local_2c = 0;
      local_28 = 0;
      local_24 = 0;
      FUN_00632920(local_c,piVar2 + 0xf);
      if (*(int *)((int)this + 0x14) == 0x4c4c554e) {
        if (*(int *)((int)this + 0x24) != 0) {
          do {
            param_1 = (int *)FUN_0082e110(DAT_00c26058);
            (**(code **)(*param_1 + 0x70))
                      (param_1,*(undefined4 *)((int)this + 0xc),*(undefined4 *)((int)this + 0x10),
                       0x4c4c554e,0,0,0,*(int *)((int)this + 0x30) + uVar6 * 4,0);
            *(undefined4 *)(*(int *)((int)this + 0x38) + uVar6 * 4) = 0;
            uVar6 = uVar6 + 1;
          } while (uVar6 < *(uint *)((int)this + 0x24));
        }
      }
      else {
        if (*(int *)((int)this + 0x24) != 0) {
          do {
            uVar4 = (**(code **)(*DAT_00c26058 + 0x234))();
            *(undefined4 *)(*(int *)((int)this + 0x38) + uVar6 * 4) = uVar4;
            uVar4 = (**(code **)(**(int **)(*(int *)((int)this + 0x38) + uVar6 * 4) + 0x14))();
            *(undefined4 *)((int)this + 0xc) = uVar4;
            uVar4 = (**(code **)(**(int **)(*(int *)((int)this + 0x38) + uVar6 * 4) + 0x18))();
            uVar6 = uVar6 + 1;
            *(undefined4 *)((int)this + 0x10) = uVar4;
          } while (uVar6 < *(uint *)((int)this + 0x24));
        }
        uVar6 = 0;
        if (*(int *)((int)this + 0x2c) != 0) {
          do {
            if (*(int *)((int)this + 8) == 0) {
              piVar5 = FUN_00838410(*(int *)(*(int *)((int)this + 0x38) + uVar6 * 4),0,0);
              *(int **)(*(int *)((int)this + 0x30) + uVar6 * 4) = piVar5;
            }
            else {
              piVar5 = FUN_00838410(**(int **)((int)this + 0x38),0,uVar6);
              *(int **)(*(int *)((int)this + 0x30) + uVar6 * 4) = piVar5;
            }
            uVar6 = uVar6 + 1;
          } while (uVar6 < *(uint *)((int)this + 0x2c));
        }
      }
      FUN_00824440((int)&local_44);
    }
    else {
      uVar6 = 0;
      if (*(int *)((int)this + 0x24) != 0) {
        do {
          *(undefined4 *)(*(int *)((int)this + 0x38) + uVar6 * 4) =
               *(undefined4 *)(piVar2[10] + uVar6 * 4);
          FUN_00839e20((int *)(*(int *)(*(int *)((int)this + 0x38) + uVar6 * 4) + 4));
          uVar4 = (**(code **)(**(int **)(*(int *)((int)this + 0x38) + uVar6 * 4) + 0x14))();
          *(undefined4 *)((int)this + 0xc) = uVar4;
          uVar4 = (**(code **)(**(int **)(*(int *)((int)this + 0x38) + uVar6 * 4) + 0x18))();
          uVar6 = uVar6 + 1;
          *(undefined4 *)((int)this + 0x10) = uVar4;
        } while (uVar6 < *(uint *)((int)this + 0x24));
      }
      uVar6 = 0;
      if (*(int *)((int)this + 0x2c) != 0) {
        do {
          if (*(int *)((int)this + 8) == 0) {
            piVar5 = FUN_00838410(*(int *)(*(int *)((int)this + 0x38) + uVar6 * 4),0,0);
            *(int **)(*(int *)((int)this + 0x30) + uVar6 * 4) = piVar5;
          }
          else {
            piVar5 = FUN_00838410(**(int **)((int)this + 0x38),0,uVar6);
            *(int **)(*(int *)((int)this + 0x30) + uVar6 * 4) = piVar5;
          }
          uVar6 = uVar6 + 1;
        } while (uVar6 < *(uint *)((int)this + 0x2c));
      }
    }
  }
  if (*(uint *)((int)this + 0x28) != 0) {
    lVar1 = (ulonglong)*(uint *)((int)this + 0x28) * 4;
    uVar4 = FUN_008868c0(-(uint)((int)((ulonglong)lVar1 >> 0x20) != 0) | (uint)lVar1);
    *(undefined4 *)((int)this + 0x34) = uVar4;
    lVar1 = (ulonglong)*(uint *)((int)this + 0x28) * 4;
    uVar4 = FUN_008868c0(-(uint)((int)((ulonglong)lVar1 >> 0x20) != 0) | (uint)lVar1);
    *(undefined4 *)((int)this + 0x3c) = uVar4;
    if (piVar2[0xb] == 0) {
      FUN_008243e0(&local_44);
      local_40 = FUN_0082f190(*(uint *)((int)this + 0x18));
      local_38 = *(undefined4 *)((int)this + 0xc);
      local_34 = *(undefined4 *)((int)this + 0x10);
      local_39 = *(undefined1 *)((int)this + 0x1e);
      uVar6 = 0;
      local_3c = 0;
      local_3b = 0;
      local_3a = 1;
      local_30 = 1;
      local_2c = 0;
      local_28 = 0;
      local_24 = 0;
      local_1c = 1;
      piVar5 = FUN_00631740(&local_8," [Depth]");
      piVar5 = FUN_00632c10(&param_1,piVar2 + 0xf,piVar5);
      FUN_00632920(local_c,piVar5);
      FUN_006310c0((int *)&param_1);
      FUN_006310c0(&local_8);
      if (*(int *)((int)this + 0x28) != 0) {
        do {
          uVar4 = (**(code **)(*DAT_00c26058 + 0x234))();
          *(undefined4 *)(*(int *)((int)this + 0x3c) + uVar6 * 4) = uVar4;
          piVar5 = FUN_00838410(*(int *)(*(int *)((int)this + 0x3c) + uVar6 * 4),0,0);
          *(int **)(*(int *)((int)this + 0x34) + uVar6 * 4) = piVar5;
          uVar6 = uVar6 + 1;
        } while (uVar6 < *(uint *)((int)this + 0x28));
      }
      FUN_00824440((int)&local_44);
    }
    else {
      uVar6 = 0;
      if (*(int *)((int)this + 0x28) != 0) {
        do {
          *(undefined4 *)(*(int *)((int)this + 0x3c) + uVar6 * 4) =
               *(undefined4 *)(piVar2[0xb] + uVar6 * 4);
          FUN_00839e20((int *)(*(int *)(*(int *)((int)this + 0x3c) + uVar6 * 4) + 4));
          piVar5 = FUN_00838410(*(int *)(*(int *)((int)this + 0x3c) + uVar6 * 4),0,0);
          *(int **)(*(int *)((int)this + 0x34) + uVar6 * 4) = piVar5;
          uVar6 = uVar6 + 1;
        } while (uVar6 < *(uint *)((int)this + 0x28));
      }
    }
  }
  FUN_008535d0(this,(byte)piVar2[9]);
  if (*(char *)((int)this + 0x1c) != '\0') {
    bVar3 = FUN_0082e340((int)DAT_00c26058,*(undefined4 *)((int)this + 0x14));
    *(bool *)((int)this + 0x51) = bVar3;
  }
  return this;
}
